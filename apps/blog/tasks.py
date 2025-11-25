# -*- coding: utf-8 -*-
"""
Celery tasks for blog automation
"""

import logging
from celery import shared_task
from django.utils import timezone
from .models import BlogPost
from .gemini_client import GeminiClient
from .salon_board_client import SALONBoardClient

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_blog_content_task(self, post_id: int):
    """
    Celery task to generate blog content using Gemini AI

    Args:
        post_id: BlogPost ID

    Returns:
        Dictionary with generation result
    """
    try:
        logger.info(f"Starting AI content generation for post {post_id}")

        # Get blog post
        try:
            post = BlogPost.objects.get(id=post_id)
        except BlogPost.DoesNotExist:
            logger.error(f"BlogPost {post_id} not found")
            return {'success': False, 'error': 'Blog post not found'}

        # Validate post status
        if post.status != 'generating':
            logger.warning(f"Post {post_id} status is {post.status}, expected 'generating'")
            # Continue anyway in case status was manually changed

        # Check if prompt exists
        if not post.ai_prompt:
            logger.error(f"Post {post_id} has no AI prompt")
            post.status = 'failed'
            post.save(update_fields=['status'])
            return {'success': False, 'error': 'No AI prompt provided'}

        # Initialize Gemini client
        gemini_client = GeminiClient()

        # Generate content
        try:
            result = gemini_client.generate_blog_content(
                prompt=post.ai_prompt,
                title=post.title if post.title else None,
            )

            # Update post with generated content
            post.title = result['title']
            post.content = result['content']
            post.ai_generated = True
            post.status = 'ready'
            post.save(update_fields=['title', 'content', 'ai_generated', 'status'])

            logger.info(f"Successfully generated content for post {post_id}")

            return {
                'success': True,
                'post_id': post_id,
                'title': result['title'],
                'model': result.get('model', 'unknown'),
                'tokens': {
                    'prompt': result.get('prompt_tokens', 0),
                    'completion': result.get('completion_tokens', 0),
                }
            }

        except Exception as e:
            logger.error(f"AI generation failed for post {post_id}: {e}")
            post.status = 'failed'
            post.save(update_fields=['status'])

            # Retry task if retries available
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

            return {'success': False, 'error': str(e), 'post_id': post_id}

    except Exception as e:
        logger.error(f"Unexpected error in generate_blog_content_task: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=3)
def publish_to_salon_board_task(self, post_id: int):
    """
    Celery task to publish blog post to SALON BOARD

    Args:
        post_id: BlogPost ID

    Returns:
        Dictionary with publication result
    """
    try:
        logger.info(f"Starting SALON BOARD publication for post {post_id}")

        # Get blog post
        try:
            post = BlogPost.objects.select_related('user', 'user__salon_board_account').get(id=post_id)
        except BlogPost.DoesNotExist:
            logger.error(f"BlogPost {post_id} not found")
            return {'success': False, 'error': 'Blog post not found'}

        # Validate post status
        if post.status != 'publishing':
            logger.warning(f"Post {post_id} status is {post.status}, expected 'publishing'")

        # Validate content
        if not post.title or not post.content:
            logger.error(f"Post {post_id} missing title or content")
            post.status = 'failed'
            post.save(update_fields=['status'])
            return {'success': False, 'error': 'Missing title or content'}

        # Get SALON BOARD account
        try:
            salon_account = post.user.salon_board_account
            if not salon_account.is_active:
                raise Exception("SALON BOARD account is not active")
        except Exception as e:
            logger.error(f"SALON BOARD account error for post {post_id}: {e}")
            post.status = 'failed'
            post.save(update_fields=['status'])
            return {'success': False, 'error': str(e)}

        # Initialize SALON BOARD client and publish
        try:
            with SALONBoardClient() as client:
                # Login
                login_success = client.login(
                    email=salon_account.email,
                    encrypted_password=salon_account.encrypted_password
                )

                if not login_success:
                    raise Exception("Failed to login to SALON BOARD")

                # Publish post
                result = client.publish_blog_post(
                    title=post.title,
                    content=post.content,
                )

                if result['success']:
                    # Update post with publication info
                    post.status = 'published'
                    post.salon_board_url = result['url']
                    post.published_at = timezone.now()
                    post.save(update_fields=['status', 'salon_board_url', 'published_at'])

                    logger.info(f"Successfully published post {post_id} to SALON BOARD")

                    return {
                        'success': True,
                        'post_id': post_id,
                        'url': result['url'],
                    }
                else:
                    raise Exception(result.get('message', 'Publication failed'))

        except Exception as e:
            logger.error(f"SALON BOARD publication failed for post {post_id}: {e}")
            post.status = 'failed'
            post.save(update_fields=['status'])

            # Retry task if retries available
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=120 * (self.request.retries + 1))

            return {'success': False, 'error': str(e), 'post_id': post_id}

    except Exception as e:
        logger.error(f"Unexpected error in publish_to_salon_board_task: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def cleanup_old_failed_posts():
    """
    Periodic task to clean up old failed posts

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
