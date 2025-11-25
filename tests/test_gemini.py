#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gemini API Integration Test
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.blog.gemini_client import GeminiClient
from django.conf import settings

def test_gemini_integration():
    """Test Gemini API integration"""

    print("=" * 60)
    print("Testing Gemini API Integration")
    print("=" * 60)

    # Check API key
    if not settings.GEMINI_API_KEY:
        print("\n❌ ERROR: GEMINI_API_KEY not configured")
        return False

    print(f"\n✓ API Key configured: {settings.GEMINI_API_KEY[:20]}...")

    # Initialize client
    try:
        client = GeminiClient()
        print(f"✓ Gemini client initialized")
        print(f"  Model: {client.model_id}")
    except Exception as e:
        print(f"\n❌ ERROR: Failed to initialize Gemini client: {e}")
        return False

    # Test 1: Simple content generation
    print("\n" + "-" * 60)
    print("Test 1: Blog Content Generation")
    print("-" * 60)

    prompt = """
冬のヘアケアについて、300文字程度のブログ記事を作成してください。
タイトルも含めてJSON形式で返してください。
"""

    try:
        print(f"\nPrompt: {prompt.strip()}")
        print("\nGenerating content...")

        result = client.generate_blog_content(
            prompt=prompt,
            temperature=0.7,
            max_output_tokens=1000
        )

        print("\n✓ Content generated successfully!")
        print(f"\nTitle: {result['title']}")
        print(f"\nContent (first 200 chars):\n{result['content'][:200]}...")
        print(f"\nModel: {result['model']}")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: Content generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_gemini_integration()

    print("\n" + "=" * 60)
    if success:
        print("✓ Gemini Integration Test: PASSED")
    else:
        print("❌ Gemini Integration Test: FAILED")
    print("=" * 60)

    sys.exit(0 if success else 1)
