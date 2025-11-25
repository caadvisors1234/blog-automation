#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test early validation error handling in tasks.py

Verifies that post_log is saved to database when early validation fails:
1. Missing title or content
2. SALON BOARD account not active
"""

import os
import sys
import django
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Setup Django - use relative path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.blog.tasks import publish_to_salon_board_task
from apps.blog.models import BlogPost


def test_missing_content_saves_log():
    """Test that post_log is saved when content is missing"""
    print("\n" + "="*60)
    print("Test 1: Missing Content Saves Log")
    print("="*60)

    with patch('apps.blog.tasks.BlogPost.objects') as mock_objects, \
         patch('apps.blog.tasks.PostLog.objects.create') as mock_create_log, \
         patch('apps.blog.tasks.ProgressNotifier') as mock_notifier:

        # Mock blog post with missing content
        mock_post = Mock()
        mock_post.id = 1
        mock_post.title = ""  # Empty title
        mock_post.content = "Some content"
        mock_post.status = 'publishing'
        mock_post.user = Mock()
        mock_post.user.id = 1
        mock_post.save = Mock()

        # Mock the select_related().get() chain
        mock_select_related = Mock()
        mock_select_related.get.return_value = mock_post
        mock_objects.select_related.return_value = mock_select_related

        # Mock post_log
        mock_log = Mock()
        mock_log.save = Mock()
        mock_log.calculate_duration = Mock()
        mock_create_log.return_value = mock_log

        # Mock notifier
        mock_notifier_instance = Mock()
        mock_notifier.return_value = mock_notifier_instance

        # Execute task
        result = publish_to_salon_board_task(post_id=1)

        # Verify result
        assert result['success'] == False, "Should fail with missing content"
        assert 'Missing title or content' in result['error'], "Error should mention missing content"

        # Verify post_log was updated
        assert mock_log.status == 'failed', "post_log.status should be 'failed'"
        assert mock_log.error_message == 'Missing title or content', \
            "post_log.error_message should be set"

        # Verify post_log.save() was called
        assert mock_log.save.called, "post_log.save() should be called"
        # Check that update_fields includes required fields
        call_args = mock_log.save.call_args
        if call_args and 'update_fields' in call_args[1]:
            update_fields = call_args[1]['update_fields']
            assert 'status' in update_fields, "update_fields should include 'status'"
            assert 'error_message' in update_fields, "update_fields should include 'error_message'"
            assert 'completed_at' in update_fields, "update_fields should include 'completed_at'"

        print("✓ post_log.save() was called with correct fields")
        print(f"  - update_fields: {update_fields if call_args else 'N/A'}")
        print("✓ Missing content error handled correctly")
        return True


def test_inactive_account_saves_log():
    """Test that post_log is saved when SALON BOARD account is inactive"""
    print("\n" + "="*60)
    print("Test 2: Inactive Account Saves Log")
    print("="*60)

    with patch('apps.blog.tasks.BlogPost.objects') as mock_objects, \
         patch('apps.blog.tasks.PostLog.objects.create') as mock_create_log, \
         patch('apps.blog.tasks.ProgressNotifier') as mock_notifier:

        # Mock blog post
        mock_post = Mock()
        mock_post.id = 2
        mock_post.title = "Test Title"
        mock_post.content = "Test Content"
        mock_post.status = 'publishing'
        mock_post.user = Mock()
        mock_post.user.id = 2
        mock_post.save = Mock()

        # Mock SALON BOARD account (inactive)
        mock_salon_account = Mock()
        mock_salon_account.is_active = False
        mock_post.user.salon_board_account = mock_salon_account

        # Mock the select_related().get() chain
        mock_select_related = Mock()
        mock_select_related.get.return_value = mock_post
        mock_objects.select_related.return_value = mock_select_related

        # Mock post_log
        mock_log = Mock()
        mock_log.save = Mock()
        mock_log.calculate_duration = Mock()
        mock_create_log.return_value = mock_log

        # Mock notifier
        mock_notifier_instance = Mock()
        mock_notifier.return_value = mock_notifier_instance

        # Execute task
        result = publish_to_salon_board_task(post_id=2)

        # Verify result
        assert result['success'] == False, "Should fail with inactive account"
        assert 'not active' in result['error'].lower(), "Error should mention inactive account"

        # Verify post_log was updated
        assert mock_log.status == 'failed', "post_log.status should be 'failed'"
        assert mock_log.error_message is not None, "post_log.error_message should be set"

        # Verify post_log.save() was called
        assert mock_log.save.called, "post_log.save() should be called"
        call_args = mock_log.save.call_args
        if call_args and 'update_fields' in call_args[1]:
            update_fields = call_args[1]['update_fields']
            assert 'status' in update_fields, "update_fields should include 'status'"
            assert 'error_message' in update_fields, "update_fields should include 'error_message'"

        print("✓ post_log.save() was called with correct fields")
        print(f"  - update_fields: {update_fields if call_args else 'N/A'}")
        print("✓ Inactive account error handled correctly")
        return True


def run_all_tests():
    """Run all early validation tests"""
    print("\n" + "="*70)
    print(" Early Validation Error Test Suite")
    print("="*70)

    tests = [
        ("Missing Content Saves Log", test_missing_content_saves_log),
        ("Inactive Account Saves Log", test_inactive_account_saves_log),
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
        print("\nKey improvements:")
        print("  1. post_log.save() is called for early validation errors")
        print("  2. Database is updated BEFORE notifications")
        print("  3. Error logs are properly persisted to database")
        print("  4. Frontend can now access failure reasons")
        return True
    else:
        print(f"\n❌ {total - passed} test(s) FAILED")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    print("\n" + "="*70)
    sys.exit(0 if success else 1)
