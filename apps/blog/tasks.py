# -*- coding: utf-8 -*-
"""
Celery tasks for blog automation with real-time progress notifications.

This module contains Celery tasks for:
- AI blog content generation (Gemini)
- SALON BOARD automatic publishing (Playwright)
- Periodic cleanup tasks

All tasks support WebSocket progress notifications via Django Channels.
"""

import logging
import os
from celery import shared_task
from django.utils import timezone
from django.db import IntegrityError
from .models import BlogPost, PostLog
from .gemini_client import GeminiClient
from .salon_board_client import (
    SALONBoardClient, 
    SALONBoardError,
    LoginError, 
    RobotDetectionError, 
    SalonSelectionError,
    ElementNotFoundError,
    UploadError
)
from .progress import ProgressNotifier

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_blog_content_task(self, post_id: int, template_id: str = ''):
    """
    Celery task to generate 3 blog content variations using Gemini AI.

    Sends real-time progress updates via WebSocket.
    Generates 3 article variations for user selection.

    Args:
        post_id: BlogPost ID
        template_id: Optional BlogPostTemplate ID to append to generated content

    Returns:
        Dictionary with generation result including 3 variations
    """
    notifier = None

    try:
        logger.info(f"Starting AI content generation (3 variations) for post {post_id}")

        # Get blog post
        try:
            post = BlogPost.objects.select_related('user').get(id=post_id)
        except BlogPost.DoesNotExist:
            logger.error(f"BlogPost {post_id} not found")
            return {'success': False, 'error': 'Blog post not found'}

        # Get template content if template_id is provided
        template_content = ''
        if template_id:
            try:
                from .models import BlogPostTemplate
                template = BlogPostTemplate.objects.get(id=template_id, user=post.user)
                template_content = template.content
                logger.info(f"Using template '{template.name}' for post {post_id}")
            except BlogPostTemplate.DoesNotExist:
                logger.warning(f"Template {template_id} not found for user {post.user.id}")
            except Exception as e:
                logger.error(f"Error loading template {template_id}: {e}")

        # Initialize progress notifier
        notifier = ProgressNotifier(
            post_id=post_id,
            user_id=post.user.id,
            task_type=ProgressNotifier.TASK_TYPE_GENERATE,
            task_id=self.request.id
        )
        
        # Send task started notification
        notifier.send_started("AI記事生成を開始しました（3案作成中）")
        notifier.send_progress(5, "準備中...")

        # Validate post status
        if post.status != 'generating':
            logger.warning(f"Post {post_id} status is {post.status}, expected 'generating'")
            # Continue anyway in case status was manually changed

        keywords = (post.keywords or '').strip()
        custom_prompt = (post.ai_prompt or '').strip()
        image_paths = [img.file_path for img in post.images.all().order_by('order')]
        current_year = timezone.now().year

        # Check if keywords exist (required)
        if not keywords:
            logger.error(f"Post {post_id} has no keywords")
            post.status = 'failed'
            post.save(update_fields=['status'])
            notifier.send_failed(
                error='No keywords provided',
                message='キーワードが指定されていません'
            )
            return {'success': False, 'error': 'No keywords provided'}

        notifier.send_progress(10, "プロンプトを準備中...")

        # Initialize Gemini client
        gemini_client = GeminiClient()

        # Build prompt (respect user-specified prompt if any)
        image_count = post.images.count()

        click_words = "失敗しない,〇選,人気,最新版,簡単"
        guidance = """記事タイプを判断して執筆すること：
- How to/ポイント解説系: 手順やコツを整理し、読者がすぐ実践できる形にする
- スタイルまとめ系: トレンドやデザイン例を複数提示し、雰囲気が伝わるようにする"""

        image_filenames_text = ""
        if image_paths:
            image_filenames_text = "【アップロード画像（順番はimage_1, image_2...に対応）】\n" + "\n".join(
                [f"{idx+1}. {os.path.basename(path)}" for idx, path in enumerate(image_paths)]
            )

        if custom_prompt:
            full_prompt = f"""{custom_prompt}

【キーワード】
{keywords}

【要件】
- 美容サロンのお客様向けに親しみやすく読みやすい記事にする
- タイトルは25文字以内で、クリックを誘うワード（例: {click_words} のいずれか）を1つ以上入れる
- 可能であれば「{current_year}年版」を自然に含める
- 本文は500〜600文字程度（最大1000文字厳守）
- {guidance}
- 添付した画像の内容を踏まえ、適切な位置にプレースホルダーを配置する
- キーワードを自然に含め、読者が行動したくなるように導く
{image_filenames_text}

【重要な制約】
- マークダウン記法は一切使用禁止（**太字**、*斜体*、#見出し、- リスト、[]()リンクなど）
- プレーンテキストのみで記述
- 改行や段落分けは通常の改行のみ使用
- 記号による装飾は使わない"""
        else:
            full_prompt = f"""以下のキーワードに基づいて、美容サロンのブログ記事を作成してください。

【キーワード】
{keywords}

【要件】
- 美容サロンのお客様向けに親しみやすく読みやすい記事にする
- タイトルは25文字以内で、クリックを誘うワード（例: {click_words} のいずれか）を1つ以上入れる
- 可能であれば「{current_year}年版」を自然に含める
- 本文は500〜600文字程度（最大1000文字厳守）
- {guidance}
- 添付した画像の内容を踏まえ、適切な位置にプレースホルダーを配置する
- キーワードを自然に含め、読者が行動したくなるように導く
{image_filenames_text}

【重要な制約】
- マークダウン記法は一切使用禁止（**太字**、*斜体*、#見出し、- リスト、[]()リンクなど）
- プレーンテキストのみで記述
- 改行や段落分けは通常の改行のみ使用
- 記号による装飾は使わない"""

        if image_count > 0:
            full_prompt += f"""

【画像について】
{image_count}枚の画像がアップロードされています。
本文中に {{{{image_1}}}} から {{{{image_{image_count}}}}} までのプレースホルダーを適切な位置に配置してください。
画像はヘアスタイルやサロンの様子を表しています。"""

        notifier.send_progress(20, "Gemini AIに送信中...")

        # Generate 3 content variations
        try:
            notifier.send_progress(30, "AIが3つの記事案を生成中... (これには数秒〜十数秒かかります)")
            
            result = gemini_client.generate_blog_content_variations(
                prompt=full_prompt,
                num_variations=3,
                image_count=image_count,
                image_paths=image_paths,
            )

            notifier.send_progress(80, "生成完了。データベースを更新中...")

            # Truncate title and content for each variation, and append template if provided
            for variation in result['variations']:
                # Truncate title to 25 characters
                if 'title' in variation and len(variation['title']) > 25:
                    logger.warning(
                        f"Post {post_id} variation title exceeds 25 chars "
                        f"({len(variation['title'])} chars), truncating..."
                    )
                    variation['title'] = variation['title'][:25]

                # Append template content if provided
                if template_content and 'content' in variation:
                    current_content = variation['content']
                    separator = '\n\n' if current_content and not current_content.endswith('\n') else '\n'
                    combined_content = current_content + separator + template_content

                    # Check if combined content exceeds 1000 chars
                    if len(combined_content) > 1000:
                        logger.warning(
                            f"Post {post_id} variation content with template exceeds 1000 chars "
                            f"({len(combined_content)} chars), truncating base content..."
                        )
                        # Truncate base content to make room for template
                        available_space = 1000 - len(separator) - len(template_content)
                        if available_space > 0:
                            variation['content'] = current_content[:available_space] + separator + template_content
                        else:
                            # Template alone exceeds 1000 chars, just truncate combined
                            variation['content'] = combined_content[:1000]
                    else:
                        variation['content'] = combined_content

                # Truncate content to 1000 characters if no template
                elif 'content' in variation and len(variation['content']) > 1000:
                    logger.warning(
                        f"Post {post_id} variation content exceeds 1000 chars "
                        f"({len(variation['content'])} chars), truncating..."
                    )
                    variation['content'] = variation['content'][:1000]

            # Update post with generated variations
            # Refresh from database to avoid stale object issues
            post.refresh_from_db()
            old_status = post.status
            post.generated_variations = result['variations']
            post.ai_generated = True
            post.status = 'selecting'  # User needs to select from variations
            post.save(update_fields=['generated_variations', 'ai_generated', 'status'])

            notifier.send_status_update(old_status, 'selecting')
            notifier.send_progress(100, "3つの記事案が生成されました。選択画面に移動します。")

            logger.info(f"Successfully generated 3 content variations for post {post_id}")

            # Send completion notification with variations info
            notifier.send_completed(
                result={
                    'post_id': post_id,
                    'variation_count': len(result['variations']),
                    'model': result.get('model', 'unknown'),
                    'redirect_url': f'/blog/posts/{post_id}/select/',
                },
                message="3つの記事案が生成されました。お好みの記事を選択してください。"
            )

            return {
                'success': True,
                'post_id': post_id,
                'variation_count': len(result['variations']),
                'model': result.get('model', 'unknown'),
            }

        except Exception as e:
            logger.error(f"AI generation failed for post {post_id}: {e}")
            post.status = 'failed'
            post.save(update_fields=['status'])

            # Retry task if retries available
            if self.request.retries < self.max_retries:
                notifier.send_progress(
                    0,
                    f"エラーが発生しました。リトライ中... ({self.request.retries + 1}/{self.max_retries})"
                )
                raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

            notifier.send_failed(
                error=str(e),
                message='AI記事生成に失敗しました',
                retry_count=self.request.retries
            )
            return {'success': False, 'error': str(e), 'post_id': post_id}

    except Exception as e:
        logger.error(f"Unexpected error in generate_blog_content_task: {e}")
        if notifier:
            notifier.send_failed(
                error=str(e),
                message='予期せぬエラーが発生しました'
            )
        return {'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=3)
def publish_to_salon_board_task(self, post_id: int, log_id: int = None):
    """
    Celery task to publish blog post to SALON BOARD.
    
    Sends real-time progress updates via WebSocket.

    Args:
        post_id: BlogPost ID
        log_id: PostLog ID (optional)

    Returns:
        Dictionary with publication result
    """
    post_log = None
    notifier = None

    try:
        logger.info(f"Starting SALON BOARD publication for post {post_id}")

        # Get blog post
        try:
            post = BlogPost.objects.select_related('user', 'user__salon_board_account').get(id=post_id)
        except BlogPost.DoesNotExist:
            logger.error(f"BlogPost {post_id} not found")
            return {'success': False, 'error': 'Blog post not found'}

        # Initialize progress notifier
        notifier = ProgressNotifier(
            post_id=post_id,
            user_id=post.user.id,
            task_type=ProgressNotifier.TASK_TYPE_PUBLISH,
            task_id=self.request.id
        )
        
        # Send task started notification
        notifier.send_started("SALON BOARDへの投稿を開始しました")
        notifier.send_progress(5, "準備中...")

        # Get or create post log
        if log_id:
            try:
                post_log = PostLog.objects.get(id=log_id)
            except PostLog.DoesNotExist:
                pass

        if not post_log:
            existing_log = getattr(post, 'log', None)
            if existing_log:
                post_log = existing_log
            else:
                try:
                    post_log = PostLog.objects.create(
                        user=post.user,
                        blog_post=post,
                        status='in_progress',
                        started_at=timezone.now()
                    )
                except IntegrityError:
                    post_log = PostLog.objects.get(blog_post=post)

        # Ensure log is reset to in_progress state
        if post_log:
            post_log.status = 'in_progress'
            post_log.error_message = ''
            post_log.screenshot_path = ''
            post_log.scraping_data = {}
            post_log.started_at = timezone.now()
            post_log.completed_at = None
            post_log.duration_seconds = 0
            try:
                post_log.save(update_fields=[
                    'status', 'error_message', 'screenshot_path',
                    'scraping_data', 'started_at', 'completed_at', 'duration_seconds'
                ])
            except Exception as log_error:
                logger.error(f"Failed to reset post log {post_log.id}: {log_error}")

        # Validate post status
        if post.status != 'publishing':
            logger.warning(f"Post {post_id} status is {post.status}, expected 'publishing'")

        # Validate content
        if not post.title or not post.content:
            logger.error(f"Post {post_id} missing title or content")

            # Save to database BEFORE sending notifications
            try:
                post.status = 'failed'
                post.save(update_fields=['status'])
                post_log.status = 'failed'
                post_log.error_message = 'Missing title or content'
                post_log.completed_at = timezone.now()
                post_log.calculate_duration()
                post_log.save(update_fields=['status', 'error_message', 'completed_at', 'duration_seconds'])
            except Exception as db_error:
                logger.error(f"Failed to save to database: {db_error}")

            # Send notification after database operations
            try:
                notifier.send_failed(
                    error='Missing title or content',
                    message='タイトルまたは本文がありません'
                )
            except Exception as notif_error:
                logger.error(f"Failed to send notification: {notif_error}")

            return {'success': False, 'error': 'Missing title or content'}

        notifier.send_progress(10, "認証情報を確認中...")

        # Get SALON BOARD account
        try:
            salon_account = post.user.salon_board_account
            if not salon_account.is_active:
                raise Exception("SALON BOARD account is not active")
        except Exception as e:
            logger.error(f"SALON BOARD account error for post {post_id}: {e}")

            # Save to database BEFORE sending notifications
            try:
                post.status = 'failed'
                post.save(update_fields=['status'])
                post_log.status = 'failed'
                post_log.error_message = str(e)
                post_log.completed_at = timezone.now()
                post_log.calculate_duration()
                post_log.save(update_fields=['status', 'error_message', 'completed_at', 'duration_seconds'])
            except Exception as db_error:
                logger.error(f"Failed to save to database: {db_error}")

            # Send notification after database operations
            try:
                notifier.send_failed(
                    error=str(e),
                    message='SALON BOARDアカウントの認証情報を取得できませんでした'
                )
            except Exception as notif_error:
                logger.error(f"Failed to send notification: {notif_error}")

            return {'success': False, 'error': str(e)}

        # Get credentials
        login_id, password = salon_account.get_credentials()

        # Get image paths
        image_paths = [img.file_path for img in post.images.all().order_by('order')]
        
        notifier.send_progress(15, f"画像{len(image_paths)}枚を準備しました")

        publication_result = None
        publication_completed = False

        # Initialize SALON BOARD client and publish
        try:
            notifier.send_progress(20, "ブラウザを起動中...")

            with SALONBoardClient() as client:
                notifier.send_progress(30, "SALON BOARDにログイン中...")

                # Login (raises LoginError or RobotDetectionError on failure)
                client.login(
                    login_id=login_id,
                    password=password
                )

                notifier.send_progress(50, "ログイン成功。投稿を作成中...")

                # Publish post
                publication_result = client.publish_blog_post(
                    title=post.title,
                    content=post.content,
                    image_paths=image_paths,
                    stylist_id=post.stylist_id,
                    coupon_name=post.coupon_name,
                    salon_id=post.user.hpb_salon_id,
                )

            if publication_result and publication_result.get('success'):
                publication_completed = True
                # Save to database BEFORE sending notifications
                try:
                    old_status = post.status
                    post.status = 'published'
                    post.salon_board_url = publication_result.get('url', '')
                    post.published_at = timezone.now()
                    post.save(update_fields=['status', 'salon_board_url', 'published_at'])

                    post_log.status = 'success'
                    post_log.screenshot_path = publication_result.get('screenshot_path', '')
                    post_log.completed_at = timezone.now()
                    post_log.calculate_duration()
                    # calculate_duration() already saves with update_fields=['duration_seconds']
                    # Save remaining fields
                    post_log.save(update_fields=['status', 'screenshot_path', 'completed_at'])

                    logger.info(f"Successfully published post {post_id} to SALON BOARD")
                except Exception as db_error:
                    logger.error(f"Failed to save to database: {db_error}")
                    raise

                # Send notifications after database operations
                try:
                    notifier.send_status_update(old_status, 'published')
                    notifier.send_progress(100, "投稿が完了しました")
                    notifier.send_completed(
                        result={
                            'post_id': post_id,
                            'url': publication_result.get('url', ''),
                        },
                        message='SALON BOARDへの投稿が完了しました'
                    )
                except Exception as notif_error:
                    logger.error(f"Failed to send notification: {notif_error}")

                return {
                    'success': True,
                    'post_id': post_id,
                    'url': publication_result.get('url', ''),
                }
            else:
                message = None
                if publication_result:
                    message = publication_result.get('message')
                raise SALONBoardError(message or 'Publication failed')

        except RobotDetectionError as e:
            # CAPTCHA detected - do not retry (as per system_requirements.md)
            logger.error(f"CAPTCHA detected for post {post_id}: {e}")

            # Save to database BEFORE sending notifications
            try:
                post.status = 'failed'
                post.save(update_fields=['status'])
                post_log.status = 'failed'
                post_log.error_message = f"CAPTCHA検知: {str(e)}"
                post_log.completed_at = timezone.now()
                post_log.calculate_duration()
                post_log.save()
            except Exception as db_error:
                logger.error(f"Failed to save to database: {db_error}")

            # Send notification after database operations
            try:
                notifier.send_failed(
                    error=str(e),
                    message='CAPTCHA認証が検出されました。手動での対応が必要です。'
                )
            except Exception as notif_error:
                logger.error(f"Failed to send notification: {notif_error}")

            return {'success': False, 'error': str(e), 'post_id': post_id}
        
        except LoginError as e:
            # Login failed - check credentials
            logger.error(f"Login failed for post {post_id}: {e}")

            # Save to database BEFORE sending notifications
            try:
                post.status = 'failed'
                post.save(update_fields=['status'])
                post_log.status = 'failed'
                post_log.error_message = f"ログイン失敗: {str(e)}"
                post_log.completed_at = timezone.now()
                post_log.calculate_duration()
                post_log.save()
            except Exception as db_error:
                logger.error(f"Failed to save to database: {db_error}")

            # Send notification after database operations
            try:
                notifier.send_failed(
                    error=str(e),
                    message='SALON BOARDへのログインに失敗しました。認証情報を確認してください。'
                )
            except Exception as notif_error:
                logger.error(f"Failed to send notification: {notif_error}")

            return {'success': False, 'error': str(e), 'post_id': post_id}
        
        except SalonSelectionError as e:
            # Salon not found
            logger.error(f"Salon selection failed for post {post_id}: {e}")

            # Save to database BEFORE sending notifications
            try:
                post.status = 'failed'
                post.save(update_fields=['status'])
                post_log.status = 'failed'
                post_log.error_message = f"サロン選択エラー: {str(e)}"
                post_log.completed_at = timezone.now()
                post_log.calculate_duration()
                post_log.save()
            except Exception as db_error:
                logger.error(f"Failed to save to database: {db_error}")

            # Send notification after database operations
            try:
                notifier.send_failed(
                    error=str(e),
                    message='指定されたサロンが見つかりませんでした。'
                )
            except Exception as notif_error:
                logger.error(f"Failed to send notification: {notif_error}")

            return {'success': False, 'error': str(e), 'post_id': post_id}

        except (SALONBoardError, Exception) as e:
            logger.error(f"SALON BOARD publication failed for post {post_id}: {e}")

            # Save to database BEFORE sending notifications
            try:
                post.status = 'failed'
                post.save(update_fields=['status'])

                post_log.status = 'failed'
                if publication_completed:
                    post_log.error_message = f"SALON BOARDでは公開済みですが保存に失敗: {str(e)}"
                else:
                    post_log.error_message = str(e)
                if publication_result and publication_result.get('screenshot_path'):
                    post_log.screenshot_path = publication_result.get('screenshot_path', '')
                post_log.completed_at = timezone.now()
                post_log.calculate_duration()
                post_log.save()
            except Exception as db_error:
                logger.error(f"Failed to save to database: {db_error}")

            # Retry task if retries available (for recoverable errors)
            should_retry = (not publication_completed) and (self.request.retries < self.max_retries)
            if should_retry:
                try:
                    notifier.send_progress(
                        0,
                        f"エラーが発生しました。リトライ中... ({self.request.retries + 1}/{self.max_retries})"
                    )
                except Exception as notif_error:
                    logger.error(f"Failed to send retry notification: {notif_error}")
                raise self.retry(exc=e, countdown=120 * (self.request.retries + 1))

            # Send failure notification after database operations
            try:
                failure_message = 'SALON BOARDへの投稿に失敗しました'
                if publication_completed:
                    failure_message = 'SALON BOARDでは公開済みですが、アプリ側の保存に失敗しました。管理画面で公開済みかご確認ください。'
                notifier.send_failed(
                    error=str(e),
                    message=failure_message,
                    retry_count=self.request.retries
                )
            except Exception as notif_error:
                logger.error(f"Failed to send failure notification: {notif_error}")

            return {'success': False, 'error': str(e), 'post_id': post_id}

    except Exception as e:
        logger.error(f"Unexpected error in publish_to_salon_board_task: {e}")

        # Save post_log in a safe way (avoid async context issues)
        if post_log:
            try:
                post_log.status = 'failed'
                post_log.error_message = str(e)
                post_log.completed_at = timezone.now()
                post_log.save()
            except Exception as save_error:
                logger.error(f"Failed to save post_log: {save_error}")

        # Send notification after database operations
        if notifier:
            try:
                notifier.send_failed(
                    error=str(e),
                    message='予期せぬエラーが発生しました'
                )
            except Exception as notif_error:
                logger.error(f"Failed to send notification: {notif_error}")

        return {'success': False, 'error': str(e)}
