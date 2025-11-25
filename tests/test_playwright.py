#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Playwright Basic Test
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from playwright.sync_api import sync_playwright

def test_playwright():
    """Test Playwright browser automation"""

    print("=" * 60)
    print("Testing Playwright")
    print("=" * 60)

    try:
        print("\nStarting Playwright...")
        with sync_playwright() as p:
            print("✓ Playwright started")

            # Launch browser
            print("\nLaunching Chromium browser...")
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            print("✓ Browser launched")

            # Create context
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            print("✓ Browser context created")

            # Create page
            page = context.new_page()
            print("✓ Page created")

            # Navigate to a test page
            print("\nNavigating to Google...")
            page.goto('https://www.google.com', wait_until='networkidle', timeout=30000)
            print("✓ Page loaded")

            # Get title
            title = page.title()
            print(f"\nPage title: {title}")

            # Take screenshot
            screenshot_path = '/tmp/playwright_test.png'
            page.screenshot(path=screenshot_path)
            print(f"✓ Screenshot saved: {screenshot_path}")

            # Close browser
            browser.close()
            print("✓ Browser closed")

        print("\n✓ Playwright Test: PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Playwright test failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n❌ Playwright Test: FAILED")
        return False

if __name__ == '__main__':
    success = test_playwright()

    print("\n" + "=" * 60)
    sys.exit(0 if success else 1)
