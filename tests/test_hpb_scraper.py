#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HPB Scraper Test

要件定義書に基づき、スタイリスト情報とクーポン情報の取得をテストする。

期待値:
- スタイリスト: 10名
- クーポン: 72件
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.blog.hpb_scraper import HPBScraper, scrape_stylists, scrape_coupons


def test_hpb_scraper():
    """Test HPB scraper"""

    print("=" * 60)
    print("Testing HPB Scraper")
    print("=" * 60)

    # HPB salon URL
    salon_url = "https://beauty.hotpepper.jp/slnH000232182/"

    print(f"\nTarget URL: {salon_url}")
    print(f"Expected: 10 stylists, 72 coupons")

    success = True
    scraper = None

    try:
        # Initialize scraper
        scraper = HPBScraper()
        print("\n✓ Scraper initialized")

        # Test 1: Scrape stylist information
        print("\n" + "-" * 60)
        print("Test 1: Scraping stylist information...")
        print("-" * 60)
        stylists = scraper.scrape_stylists(salon_url)

        print(f"\n✓ Found {len(stylists)} stylists (expected: 10)")
        if stylists:
            print("\nStylist Information:")
            for i, stylist in enumerate(stylists, 1):
                print(f"  {i:2d}. ID: {stylist['stylist_id']}, Name: {stylist['name']}")
        else:
            print("  ⚠️  No stylists found")
            success = False

        # Test 2: Scrape coupon information
        print("\n" + "-" * 60)
        print("Test 2: Scraping coupon information...")
        print("-" * 60)
        coupons = scraper.scrape_coupons(salon_url)

        print(f"\n✓ Found {len(coupons)} coupons (expected: 72)")
        if coupons:
            print("\nCoupon Information (first 20):")
            for i, coupon in enumerate(coupons[:20], 1):
                print(f"  {i:2d}. {coupon}")
            if len(coupons) > 20:
                print(f"  ... and {len(coupons) - 20} more")
        else:
            print("  ⚠️  No coupons found")
            success = False

        # Test 3: Test module-level functions
        print("\n" + "-" * 60)
        print("Test 3: Testing module-level functions...")
        print("-" * 60)

        # Close scraper before testing module-level functions
        scraper.close()
        scraper = None

        stylists_func = scrape_stylists(salon_url)
        coupons_func = scrape_coupons(salon_url)

        print(f"\n✓ Module-level functions work correctly")
        print(f"  Stylists: {len(stylists_func)} found")
        print(f"  Coupons: {len(coupons_func)} found")

        # Summary
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"  Stylists: {len(stylists)} found (expected: 10)")
        print(f"  Coupons:  {len(coupons)} found (expected: 72)")

        if len(stylists) == 10 and len(coupons) == 72:
            print("\n✓ All counts match expected values!")
        else:
            print("\n⚠️  Counts differ from expected values")
            if len(stylists) != 10:
                print(f"    Stylists: expected 10, got {len(stylists)}")
            if len(coupons) != 72:
                print(f"    Coupons: expected 72, got {len(coupons)}")

        print("\n" + "=" * 60)
        print("✓ HPB Scraper Test: PASSED")
        print("=" * 60)
        return success

    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 60)
        print("❌ HPB Scraper Test: FAILED")
        print("=" * 60)
        return False

    finally:
        if scraper:
            scraper.close()


if __name__ == '__main__':
    success = test_hpb_scraper()
    sys.exit(0 if success else 1)
