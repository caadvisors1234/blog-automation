#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery Task Test
"""

import os
import sys
import django
import time

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.blog.models import BlogPost
from apps.blog.tasks import generate_blog_content_task
from django.contrib.auth import get_user_model

User = get_user_model()

def test_celery_ai_generation():
    """Test Celery AI generation task"""

    print("=" * 60)
    print("Testing Celery AI Generation Task")
    print("=" * 60)

    # Get test user
    user = User.objects.get(username='testuser')
    print(f"\nUser: {user.username} (ID: {user.id})")

    # Get or create AI post
    ai_post = BlogPost.objects.filter(
        user=user,
        ai_prompt__isnull=False
    ).first()

    if not ai_post:
        print("\nCreating new AI post...")
        ai_post = BlogPost.objects.create(
            user=user,
            title="",
            content="",
            ai_prompt="春におすすめのヘアスタイルについて、800文字程度のブログ記事を書いてください。",
            ai_generated=False,
            status='draft'
        )

    print(f"\nPost ID: {ai_post.id}")
    print(f"AI Prompt: {ai_post.ai_prompt}")
    print(f"Current Status: {ai_post.status}")

    # Update status to generating
    ai_post.status = 'generating'
    ai_post.save()

    print("\nTriggering Celery task...")
    task = generate_blog_content_task.delay(ai_post.id)

    print(f"Task ID: {task.id}")
    print(f"Task State: {task.state}")

    # Wait for task to complete
    print("\nWaiting for task to complete (max 30 seconds)...")
    max_wait = 30
    elapsed = 0

    while elapsed < max_wait:
        task_state = task.state
        print(f"  [{elapsed}s] Task state: {task_state}")

        if task_state in ['SUCCESS', 'FAILURE']:
            break

        time.sleep(2)
        elapsed += 2

    # Check result
    print(f"\nFinal Task State: {task.state}")

    if task.state == 'SUCCESS':
        result = task.result
        print(f"Task Result: {result}")

        # Reload post
        ai_post.refresh_from_db()
        print(f"\nPost Status: {ai_post.status}")
        print(f"Post Title: {ai_post.title}")
        print(f"Content (first 200 chars): {ai_post.content[:200]}...")
        print(f"AI Generated: {ai_post.ai_generated}")

        print("\n✓ AI Generation Task: PASSED")
        return True

    elif task.state == 'FAILURE':
        print(f"\nTask Failed: {task.result}")
        print("\n❌ AI Generation Task: FAILED")
        return False

    else:
        print(f"\nTask did not complete within {max_wait} seconds")
        print("\n⚠ AI Generation Task: TIMEOUT")
        return False

if __name__ == '__main__':
    success = test_celery_ai_generation()

    print("\n" + "=" * 60)
    sys.exit(0 if success else 1)
