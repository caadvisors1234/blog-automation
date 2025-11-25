#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HPB Scraper Test
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.blog.hpb_scraper import HPBScraper
import json

def test_hpb_scraper():
    """Test HPB scraper"""

    print("=" * 60)
    print("Testing HPB Scraper")
    print("=" * 60)

    # HPB salon URL
    salon_url = "https://beauty.hotpepper.jp/slnH000232182/"

    print(f"\nTarget URL: {salon_url}")

    try:
        # Initialize scraper
        scraper = HPBScraper()
        print("\n✓ Scraper initialized")

        # Scrape salon info
        print("\nScraping salon information...")
        salon_info = scraper.scrape_salon_info(salon_url)

        print("\n✓ Scraping successful!")
        print("\nSalon Information:")
        print(f"  Name: {salon_info['name']}")
        print(f"  Address: {salon_info['address'][:50]}..." if len(salon_info['address']) > 50 else f"  Address: {salon_info['address']}")
        print(f"  Access: {salon_info['access'][:50]}..." if len(salon_info['access']) > 50 else f"  Access: {salon_info['access']}")
        print(f"  Description (first 100 chars): {salon_info['description'][:100]}...")
        print(f"  Images: {len(salon_info['images'])} found")
        print(f"  Styles: {len(salon_info['styles'])} found")

        if salon_info['images']:
            print(f"\n  Sample image URL: {salon_info['images'][0]}")

        if salon_info['styles']:
            print(f"\n  Sample style:")
            print(f"    Image: {salon_info['styles'][0]['image_url']}")
            print(f"    Description: {salon_info['styles'][0]['description'][:50]}...")

        # Close scraper
        scraper.close()

        print("\n✓ HPB Scraper Test: PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n❌ HPB Scraper Test: FAILED")
        return False

if __name__ == '__main__':
    success = test_hpb_scraper()

    print("\n" + "=" * 60)
    sys.exit(0 if success else 1)
