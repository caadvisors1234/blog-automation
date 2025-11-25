#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API Test Script
"""

import requests
import json
from django.contrib.auth import get_user_model

BASE_URL = "http://localhost:8000"

def test_blog_posts_api():
    """Test blog posts API endpoints"""

    print("=" * 60)
    print("Testing Blog Posts API")
    print("=" * 60)

    # Get user
    User = get_user_model()
    user = User.objects.get(username='testuser')

    print(f"\nTest User: {user.username} (ID: {user.id})")

    # Test 1: Create blog post (manual)
    print("\n1. Creating blog post (manual)...")
    from apps.blog.models import BlogPost

    post = BlogPost.objects.create(
        user=user,
        title="テスト記事：美容サロンの最新トレンド",
        content="これはテスト記事です。\n\n美容サロンの最新トレンドについて紹介します。",
        status='draft'
    )
    print(f"   Created post ID: {post.id}")
    print(f"   Title: {post.title}")
    print(f"   Status: {post.status}")

    # Test 2: Create AI-generated post
    print("\n2. Creating AI-generated blog post...")
    ai_post = BlogPost.objects.create(
        user=user,
        title="",
        content="",
        ai_prompt="冬のヘアケアについて、おすすめの方法を紹介する記事を書いてください。",
        ai_generated=False,
        status='draft'
    )
    print(f"   Created AI post ID: {ai_post.id}")
    print(f"   AI Prompt: {ai_post.ai_prompt}")
    print(f"   Status: {ai_post.status}")

    # Test 3: List all posts
    print("\n3. Listing all blog posts for user...")
    posts = BlogPost.objects.filter(user=user).order_by('-created_at')
    print(f"   Found {posts.count()} posts:")
    for p in posts:
        print(f"   - ID {p.id}: {p.title or '[AI生成待ち]'} ({p.status})")

    # Test 4: Update post status
    print("\n4. Updating post status...")
    post.status = 'ready'
    post.save()
    print(f"   Post {post.id} status updated to: {post.status}")

    # Test 5: Create SALON BOARD account
    print("\n5. Creating SALON BOARD account...")
    from apps.blog.models import SALONBoardAccount
    from cryptography.fernet import Fernet
    from django.conf import settings

    # Encrypt password
    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    encrypted_password = fernet.encrypt(b'20050715@ash10').decode()

    salon_account, created = SALONBoardAccount.objects.get_or_create(
        user=user,
        defaults={
            'email': 'CB80438',
            'encrypted_password': encrypted_password,
            'is_active': True
        }
    )

    if created:
        print(f"   Created SALON BOARD account")
    else:
        print(f"   SALON BOARD account already exists")

    print(f"   Email: {salon_account.email}")
    print(f"   Active: {salon_account.is_active}")

    print("\n" + "=" * 60)
    print("Blog Posts API Tests Completed")
    print("=" * 60)

    return {
        'manual_post_id': post.id,
        'ai_post_id': ai_post.id,
        'total_posts': posts.count()
    }

if __name__ == '__main__':
    import os
    import sys
    import django

    # Setup Django
    sys.path.insert(0, '/app')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

    result = test_blog_posts_api()

    print(f"\nTest Results:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
