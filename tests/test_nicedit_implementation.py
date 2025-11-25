#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
nicEdit Implementation Test

Tests the nicEdit implementation fixes:
1. nicEditor API usage (not iframe)
2. Cursor control
3. Success detection
"""

import os
import sys
import django
import re
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

# Setup Django - use relative path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.blog.salon_board_client import SALONBoardClient, Selectors


def test_selector_definitions():
    """Test that selectors are correctly defined"""
    print("\n" + "="*60)
    print("Test 1: Selector Definitions")
    print("="*60)

    # Check editor_div exists (not editor_iframe)
    assert hasattr(Selectors.FORM, '__getitem__'), "Selectors.FORM should be dict-like"
    assert 'editor_div' in Selectors.FORM, "editor_div should be defined"
    assert 'editor_textarea' in Selectors.FORM, "editor_textarea should be defined"

    # Verify correct selectors
    assert Selectors.FORM['editor_div'] == "div.nicEdit-main[contenteditable='true']", \
        "editor_div should target contenteditable div"
    assert Selectors.FORM['editor_textarea'] == "textarea#blogContents", \
        "editor_textarea should target textarea#blogContents"

    # Verify iframe selector is NOT present
    assert 'editor_iframe' not in Selectors.FORM, \
        "editor_iframe should not be defined (iframe doesn't exist)"

    print("✓ Selector definitions are correct")
    print("  - editor_div: div.nicEdit-main[contenteditable='true']")
    print("  - editor_textarea: textarea#blogContents")
    print("  - editor_iframe: (correctly removed)")
    return True


def test_nicedit_cursor_control():
    """Test nicEditor cursor control JavaScript"""
    print("\n" + "="*60)
    print("Test 2: nicEditor Cursor Control")
    print("="*60)

    # Create mock client
    with patch('apps.blog.salon_board_client.sync_playwright'):
        client = SALONBoardClient()
        client.page = Mock()

        # Mock evaluate to capture JavaScript
        captured_js = []
        def capture_js(js_code):
            captured_js.append(js_code)
            return True  # Simulate success

        client.page.evaluate = capture_js

        # Test cursor control method
        result = client._set_cursor_at_end_nicedit()

        assert result == True, "Cursor control should return True on success"
        assert len(captured_js) > 0, "JavaScript should be executed"

        js_code = captured_js[0]

        # Verify contenteditable div targeting
        assert 'div.nicEdit-main' in js_code, \
            "Should target div.nicEdit-main"
        assert "contenteditable='true'" in js_code or 'contenteditable="true"' in js_code, \
            "Should target contenteditable div"
        assert 'createRange' in js_code, \
            "Should use Range API for cursor control"
        assert 'getSelection' in js_code, \
            "Should use Selection API"
        assert 'selectNodeContents' in js_code, \
            "Should use selectNodeContents to select editor content"
        assert 'collapse(false)' in js_code, \
            "Should collapse range to end (false)"

        print("✓ Cursor control JavaScript is correct")
        print("  - Targets div.nicEdit-main[contenteditable='true']")
        print("  - Uses Range API for cursor positioning")
        print("  - Uses Selection API")
        print("  - Moves cursor to END of editing area")
        return True


def test_fill_content_strategy():
    """Test 3-tier fallback strategy in _fill_content_with_images"""
    print("\n" + "="*60)
    print("Test 3: Content Fill Fallback Strategy")
    print("="*60)

    with patch('apps.blog.salon_board_client.sync_playwright'):
        client = SALONBoardClient()
        client.page = Mock()

        # Mock page methods
        client.page.evaluate = Mock(return_value=True)
        client.page.locator = Mock()

        # Mock locator for editor_div
        mock_locator = Mock()
        mock_locator.count.return_value = 1
        mock_locator.evaluate = Mock()
        client.page.locator.return_value = mock_locator

        # Mock _upload_single_image
        client._upload_single_image = Mock()

        # Test content with image placeholder
        test_content = "テスト本文です。{{image_1}}画像の後のテキスト。"
        test_images = ["/path/to/image1.jpg"]

        # Execute
        client._fill_content_with_images(test_content, test_images)

        # Verify nicEditor API was attempted
        assert client.page.evaluate.called, "nicEditor API should be attempted"

        # Check for nicEditors.findEditor in any call
        evaluate_calls = [str(call) for call in client.page.evaluate.call_args_list]
        has_nicedit_api = any('nicEditors.findEditor' in call for call in evaluate_calls)
        assert has_nicedit_api, "Should attempt nicEditor API method"

        print("✓ Content fill strategy is correct")
        print("  - Attempts nicEditor API first")
        print("  - Has fallback mechanisms")
        return True


def test_success_detection():
    """Test publication success detection logic"""
    print("\n" + "="*60)
    print("Test 4: Success Detection Logic")
    print("="*60)

    with patch('apps.blog.salon_board_client.sync_playwright'):
        client = SALONBoardClient()
        client.page = Mock()

        # Test Case 1: Success message present
        print("\n  Test Case 1: Success message present")
        client.page.url = "https://salonboard.com/blog/complete"
        client.page.content.return_value = "<p>ブログの登録が完了しました。</p>"

        mock_locator = Mock()
        mock_locator.count.return_value = 1
        client.page.locator.return_value = mock_locator

        result = client._check_publication_success("/tmp/screenshot.png")
        assert result['success'] == True, "Should detect success from message"
        print("    ✓ Detected success from message")

        # Test Case 2: Back button present (completion page)
        print("\n  Test Case 2: Back button present")
        client.page.content.return_value = "<div>No success message</div>"
        mock_locator.count.return_value = 1  # Back button exists

        result = client._check_publication_success("/tmp/screenshot.png")
        assert result['success'] == True, "Should detect success from back button"
        print("    ✓ Detected success from back button (a#back)")

        # Test Case 3: Neither present
        print("\n  Test Case 3: No success indicators")
        client.page.content.return_value = "<div>Error page</div>"
        mock_locator.count.return_value = 0  # No back button

        result = client._check_publication_success("/tmp/screenshot.png")
        assert result['success'] == False, "Should fail without indicators"
        print("    ✓ Correctly fails without indicators")

        print("\n✓ Success detection logic is correct")
        print("  - Checks for 'ブログの登録が完了しました'")
        print("  - Checks for back button (a#back)")
        return True


def run_all_tests():
    """Run all nicEdit implementation tests"""
    print("\n" + "="*70)
    print(" nicEdit Implementation Test Suite")
    print("="*70)

    tests = [
        ("Selector Definitions", test_selector_definitions),
        ("nicEditor Cursor Control", test_nicedit_cursor_control),
        ("Content Fill Strategy", test_fill_content_strategy),
        ("Success Detection", test_success_detection),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result, None))
        except Exception as e:
            results.append((name, False, str(e)))
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "="*70)
    print(" Test Summary")
    print("="*70)

    passed = sum(1 for _, result, _ in results if result)
    total = len(results)

    for name, result, error in results:
        status = "✓ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
        if error:
            print(f"  Error: {error}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests PASSED")
        return True
    else:
        print(f"\n❌ {total - passed} test(s) FAILED")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    print("\n" + "="*70)
    sys.exit(0 if success else 1)
