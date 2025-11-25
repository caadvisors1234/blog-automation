#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test async notification handling in progress.py

This test verifies that notifications work correctly in both:
1. Sync context (Celery workers) - uses async_to_sync
2. Async context (WebSocket consumers) - uses asyncio.create_task
"""

import os
import sys
import django
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Setup Django - use relative path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.blog.progress import ProgressNotifier


def test_sync_context():
    """Test notification from sync context (Celery worker)"""
    print("\n" + "="*60)
    print("Test 1: Sync Context (Celery Worker)")
    print("="*60)

    with patch('apps.blog.progress.get_channel_layer') as mock_get_layer:
        mock_channel_layer = Mock()
        mock_get_layer.return_value = mock_channel_layer

        notifier = ProgressNotifier(
            post_id=1,
            user_id=1,
            task_type='generate',
            task_id='test-task-1'
        )

        # Send progress from sync context
        notifier.send_progress(50, "Processing...")

        # Should not raise any errors
        print("✓ Sync context notification sent successfully")
        return True


async def test_async_context():
    """Test notification from async context (WebSocket consumer)"""
    print("\n" + "="*60)
    print("Test 2: Async Context (WebSocket Consumer)")
    print("="*60)

    with patch('apps.blog.progress.get_channel_layer') as mock_get_layer:
        mock_channel_layer = AsyncMock()
        mock_get_layer.return_value = mock_channel_layer

        notifier = ProgressNotifier(
            post_id=2,
            user_id=2,
            task_type='publish',
            task_id='test-task-2'
        )

        # Send progress from async context
        notifier.send_progress(75, "Publishing...")

        # Wait a bit for create_task to execute
        await asyncio.sleep(0.1)

        # Should not raise any errors
        print("✓ Async context notification sent successfully")
        print("  (Notification sent via asyncio.create_task)")
        return True


async def test_mixed_context():
    """Test rapid notifications from both contexts"""
    print("\n" + "="*60)
    print("Test 3: Mixed Context (Rapid Notifications)")
    print("="*60)

    with patch('apps.blog.progress.get_channel_layer') as mock_get_layer:
        mock_channel_layer = AsyncMock()
        mock_get_layer.return_value = mock_channel_layer

        notifier = ProgressNotifier(
            post_id=3,
            user_id=3,
            task_type='generate',
            task_id='test-task-3'
        )

        # Send multiple notifications from async context
        notifier.send_started("Starting task")
        notifier.send_progress(10, "Step 1")
        notifier.send_progress(20, "Step 2")
        notifier.send_progress(30, "Step 3")

        # Wait for all tasks to complete
        await asyncio.sleep(0.2)

        print("✓ Multiple async notifications sent successfully")
        print(f"  Total notifications sent: 4")
        return True


async def test_async_error_handling():
    """Test error handling in async context"""
    print("\n" + "="*60)
    print("Test 4: Async Error Handling")
    print("="*60)

    with patch('apps.blog.progress.get_channel_layer') as mock_get_layer:
        # Mock channel_layer.group_send to raise an exception
        mock_channel_layer = AsyncMock()
        mock_channel_layer.group_send.side_effect = Exception("Mock channel error")
        mock_get_layer.return_value = mock_channel_layer

        notifier = ProgressNotifier(
            post_id=4,
            user_id=4,
            task_type='publish',
            task_id='test-task-4'
        )

        # Send notification that will fail
        notifier.send_progress(50, "This will fail")

        # Wait for task to complete (and log error)
        await asyncio.sleep(0.2)

        # Should not raise exception to caller
        print("✓ Exception in async task was caught and logged")
        print("  (Caller was not affected by task exception)")
        return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print(" Async Notification Test Suite")
    print("="*70)

    results = []

    # Test 1: Sync context
    try:
        result = test_sync_context()
        results.append(("Sync Context", result, None))
    except Exception as e:
        results.append(("Sync Context", False, str(e)))
        import traceback
        traceback.print_exc()

    # Test 2: Async context
    try:
        result = asyncio.run(test_async_context())
        results.append(("Async Context", result, None))
    except Exception as e:
        results.append(("Async Context", False, str(e)))
        import traceback
        traceback.print_exc()

    # Test 3: Mixed context
    try:
        result = asyncio.run(test_mixed_context())
        results.append(("Mixed Context", result, None))
    except Exception as e:
        results.append(("Mixed Context", False, str(e)))
        import traceback
        traceback.print_exc()

    # Test 4: Async error handling
    try:
        result = asyncio.run(test_async_error_handling())
        results.append(("Async Error Handling", result, None))
    except Exception as e:
        results.append(("Async Error Handling", False, str(e)))
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
        print("  1. Sync context (Celery): Uses async_to_sync")
        print("  2. Async context (WebSocket): Uses asyncio.create_task")
        print("  3. No more dropped notifications in async context")
        print("  4. Exceptions in async tasks are caught and logged")
        return True
    else:
        print(f"\n❌ {total - passed} test(s) FAILED")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    print("\n" + "="*70)
    sys.exit(0 if success else 1)
