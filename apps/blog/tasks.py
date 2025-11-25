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
from celery import shared_task
from django.utils import timezone
from .models import BlogPost, PostLog
from .gemini_client import GeminiClient
from .salon_board_client import SALONBoardClient
from .progress import ProgressNotifier

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_blog_content_task(self, post_id: int):
    """
    Celery task to generate 3 blog content variations using Gemini AI.
    
    Sends real-time progress updates via WebSocket.
    Generates 3 article variations for user selection.

    Args:
        post_id: BlogPost ID

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
        tone = (post.tone or '').strip()

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

        if custom_prompt:
            full_prompt = custom_prompt
            if tone:
                full_prompt = f"トーン: {tone}\n\n{full_prompt}"
            if keywords:
                full_prompt = f"キーワード: {keywords}\n\n{full_prompt}"
        else:
            full_prompt = f"""以下のキーワードに基づいて、美容サロンのブログ記事を作成してください。

【キーワード】
{keywords}

【トーン】
{tone or 'friendly'}

【要件】
- 美容サロンのお客様向けの親しみやすい記事を作成
- タイトルは25文字以内で魅力的に
- 本文は600〜800文字程度
- キーワードを自然に含める
- 読者が行動したくなるような内容に"""

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
            )

            notifier.send_progress(80, "生成完了。データベースを更新中...")

            # Update post with generated variations
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
            post_log = PostLog.objects.create(
                user=post.user,
                blog_post=post,
                status='in_progress',
                started_at=timezone.now()
            )

        # Validate post status
        if post.status != 'publishing':
            logger.warning(f"Post {post_id} status is {post.status}, expected 'publishing'")

        # Validate content
        if not post.title or not post.content:
            logger.error(f"Post {post_id} missing title or content")
            post.status = 'failed'
            post.save(update_fields=['status'])
            post_log.status = 'failed'
            post_log.error_message = 'Missing title or content'
            post_log.completed_at = timezone.now()
            post_log.calculate_duration()
            notifier.send_failed(
                error='Missing title or content',
                message='タイトルまたは本文がありません'
            )
            return {'success': False, 'error': 'Missing title or content'}

        notifier.send_progress(10, "認証情報を確認中...")

        # Get SALON BOARD account
        try:
            salon_account = post.user.salon_board_account
            if not salon_account.is_active:
                raise Exception("SALON BOARD account is not active")
        except Exception as e:
            logger.error(f"SALON BOARD account error for post {post_id}: {e}")
            post.status = 'failed'
            post.save(update_fields=['status'])
            post_log.status = 'failed'
            post_log.error_message = str(e)
            post_log.completed_at = timezone.now()
            post_log.calculate_duration()
            notifier.send_failed(
                error=str(e),
                message='SALON BOARDアカウントの認証情報を取得できませんでした'
            )
            return {'success': False, 'error': str(e)}

        # Get credentials
        login_id, password = salon_account.get_credentials()

        # Get image paths
        image_paths = [img.file_path for img in post.images.all().order_by('order')]
        
        notifier.send_progress(15, f"画像{len(image_paths)}枚を準備しました")

        # Initialize SALON BOARD client and publish
        try:
            notifier.send_progress(20, "ブラウザを起動中...")
            
            with SALONBoardClient() as client:
                notifier.send_progress(30, "SALON BOARDにログイン中...")
                
                # Login
                login_success = client.login(
                    login_id=login_id,
                    password=password
                )

                if not login_success:
                    raise Exception("Failed to login to SALON BOARD")

                notifier.send_progress(50, "ログイン成功。投稿を作成中...")

                # Publish post
                result = client.publish_blog_post(
                    title=post.title,
                    content=post.content,
                    image_paths=image_paths,
                    stylist_id=post.stylist_id,
                    coupon_name=post.coupon_name,
                    salon_id=post.user.hpb_salon_id,
                )

                if result['success']:
                    notifier.send_progress(90, "投稿完了。データベースを更新中...")
                    
                    # Update post with publication info
                    old_status = post.status
                    post.status = 'published'
                    post.salon_board_url = result.get('url', '')
                    post.published_at = timezone.now()
                    post.save(update_fields=['status', 'salon_board_url', 'published_at'])

                    # Update log
                    post_log.status = 'success'
                    post_log.screenshot_path = result.get('screenshot_path', '')
                    post_log.completed_at = timezone.now()
                    post_log.calculate_duration()

                    notifier.send_status_update(old_status, 'published')
                    notifier.send_progress(100, "投稿が完了しました")

                    logger.info(f"Successfully published post {post_id} to SALON BOARD")

                    # Send completion notification
                    notifier.send_completed(
                        result={
                            'post_id': post_id,
                            'url': result.get('url', ''),
                        },
                        message='SALON BOARDへの投稿が完了しました'
                    )

                    return {
                        'success': True,
                        'post_id': post_id,
                        'url': result.get('url', ''),
                    }
                else:
                    raise Exception(result.get('message', 'Publication failed'))

        except Exception as e:
            logger.error(f"SALON BOARD publication failed for post {post_id}: {e}")
            post.status = 'failed'
            post.save(update_fields=['status'])

            post_log.status = 'failed'
            post_log.error_message = str(e)
            post_log.completed_at = timezone.now()
            post_log.calculate_duration()

            # Retry task if retries available
            if self.request.retries < self.max_retries:
                notifier.send_progress(
                    0,
                    f"エラーが発生しました。リトライ中... ({self.request.retries + 1}/{self.max_retries})"
                )
                raise self.retry(exc=e, countdown=120 * (self.request.retries + 1))

            notifier.send_failed(
                error=str(e),
                message='SALON BOARDへの投稿に失敗しました',
                retry_count=self.request.retries
            )
            return {'success': False, 'error': str(e), 'post_id': post_id}

    except Exception as e:
        logger.error(f"Unexpected error in publish_to_salon_board_task: {e}")
        if post_log:
            post_log.status = 'failed'
            post_log.error_message = str(e)
            post_log.completed_at = timezone.now()
            post_log.save()
        if notifier:
            notifier.send_failed(
                error=str(e),
                message='予期せぬエラーが発生しました'
            )
        return {'success': False, 'error': str(e)}


@shared_task
def cleanup_old_failed_posts():
    """
    Periodic task to clean up old failed posts.

    Returns:
        Number of posts cleaned up
    """
    try:
        from datetime import timedelta

        # Delete failed posts older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count = BlogPost.objects.filter(
            status='failed',
            created_at__lt=cutoff_date
        ).delete()[0]

        logger.info(f"Cleaned up {deleted_count} old failed posts")
        return deleted_count

    except Exception as e:
        logger.error(f"Error cleaning up old posts: {e}")
        return 0


@shared_task
def cleanup_old_logs():
    """
    Periodic task to clean up old logs (6 months).

    Returns:
        Number of logs cleaned up
    """
    try:
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=180)
        deleted_count = PostLog.objects.filter(
            completed_at__lt=cutoff_date
        ).delete()[0]

        logger.info(f"Cleaned up {deleted_count} old logs")
        return deleted_count

    except Exception as e:
        logger.error(f"Error cleaning up old logs: {e}")
        return 0
