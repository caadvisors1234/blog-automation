#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verify that post_log.save() is called in early validation error handlers.

This test performs static code analysis to ensure:
1. post_log.save() is called after post_log status/error_message updates
2. Database operations occur BEFORE notifications
"""

import re
from pathlib import Path


def test_postlog_save_in_validation_errors():
    """Check that post_log.save() is called in validation error handlers"""
    print("\n" + "="*70)
    print(" PostLog Save Verification Test")
    print("="*70)

    # Use relative path to find tasks.py
    repo_root = Path(__file__).resolve().parents[1]
    tasks_file = repo_root / 'apps' / 'blog' / 'tasks.py'

    with open(tasks_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Test 1: Missing title or content validation
    print("\n" + "="*60)
    print("Test 1: Missing Title/Content Validation")
    print("="*60)

    # Find the validation block
    missing_content_pattern = r'if not post\.title or not post\.content:.*?return \{\'success\': False'
    match = re.search(missing_content_pattern, content, re.DOTALL)

    if not match:
        print("❌ FAILED: Could not find validation block")
        return False

    validation_block = match.group(0)

    # Check for post_log updates
    has_status_update = 'post_log.status = \'failed\'' in validation_block
    has_error_message = 'post_log.error_message' in validation_block
    has_completed_at = 'post_log.completed_at' in validation_block
    has_calculate_duration = 'post_log.calculate_duration()' in validation_block
    has_save = 'post_log.save(' in validation_block
    has_duration_seconds = 'duration_seconds' in validation_block

    print(f"  post_log.status update: {'✓' if has_status_update else '❌'}")
    print(f"  post_log.error_message update: {'✓' if has_error_message else '❌'}")
    print(f"  post_log.completed_at update: {'✓' if has_completed_at else '❌'}")
    print(f"  post_log.calculate_duration(): {'✓' if has_calculate_duration else '❌'}")
    print(f"  post_log.save(): {'✓' if has_save else '❌'}")
    print(f"  Correct field name (duration_seconds): {'✓' if has_duration_seconds else '❌'}")

    # Check order: save should come BEFORE notification
    save_pos = validation_block.find('post_log.save(')
    notifier_pos = validation_block.find('notifier.send_failed(')

    if save_pos > 0 and notifier_pos > 0:
        if save_pos < notifier_pos:
            print(f"  Order: Database save BEFORE notification ✓")
            order_correct_1 = True
        else:
            print(f"  Order: ❌ Notification comes before save")
            order_correct_1 = False
    else:
        print(f"  Order: Could not determine")
        order_correct_1 = False

    test1_passed = all([
        has_status_update,
        has_error_message,
        has_completed_at,
        has_calculate_duration,
        has_save,
        has_duration_seconds,
        order_correct_1
    ])

    print(f"\n{'✓ PASSED' if test1_passed else '❌ FAILED'}: Missing content validation")

    # Test 2: Inactive SALON BOARD account validation
    print("\n" + "="*60)
    print("Test 2: Inactive Account Validation")
    print("="*60)

    # Find the SALON BOARD account validation block
    # Start from "# Save to database BEFORE" comment
    account_pattern = r'logger\.error\(f"SALON BOARD account error.*?# Save to database BEFORE.*?return \{\'success\': False'
    match = re.search(account_pattern, content, re.DOTALL)

    if not match:
        print("❌ FAILED: Could not find account validation block")
        return False

    account_block = match.group(0)

    # Check for post_log updates
    has_status_update_2 = 'post_log.status = \'failed\'' in account_block
    has_error_message_2 = 'post_log.error_message' in account_block
    has_completed_at_2 = 'post_log.completed_at' in account_block
    has_calculate_duration_2 = 'post_log.calculate_duration()' in account_block
    has_save_2 = 'post_log.save(' in account_block
    has_duration_seconds_2 = 'duration_seconds' in account_block

    print(f"  post_log.status update: {'✓' if has_status_update_2 else '❌'}")
    print(f"  post_log.error_message update: {'✓' if has_error_message_2 else '❌'}")
    print(f"  post_log.completed_at update: {'✓' if has_completed_at_2 else '❌'}")
    print(f"  post_log.calculate_duration(): {'✓' if has_calculate_duration_2 else '❌'}")
    print(f"  post_log.save(): {'✓' if has_save_2 else '❌'}")
    print(f"  Correct field name (duration_seconds): {'✓' if has_duration_seconds_2 else '❌'}")

    # Check order: save should come BEFORE notification
    save_pos_2 = account_block.find('post_log.save(')
    notifier_pos_2 = account_block.find('notifier.send_failed(')

    if save_pos_2 > 0 and notifier_pos_2 > 0:
        if save_pos_2 < notifier_pos_2:
            print(f"  Order: Database save BEFORE notification ✓")
            order_correct_2 = True
        else:
            print(f"  Order: ❌ Notification comes before save")
            order_correct_2 = False
    else:
        print(f"  Order: Could not determine")
        order_correct_2 = False

    test2_passed = all([
        has_status_update_2,
        has_error_message_2,
        has_completed_at_2,
        has_calculate_duration_2,
        has_save_2,
        has_duration_seconds_2,
        order_correct_2
    ])

    print(f"\n{'✓ PASSED' if test2_passed else '❌ FAILED'}: Inactive account validation")

    # Summary
    print("\n" + "="*70)
    print(" Test Summary")
    print("="*70)

    all_passed = test1_passed and test2_passed

    if all_passed:
        print("✓ All validation handlers properly save post_log to database")
        print("\nKey improvements verified:")
        print("  1. post_log.save() is called in all validation error handlers")
        print("  2. Database operations occur BEFORE notifications")
        print("  3. All required fields are updated (status, error_message, completed_at)")
        print("  4. Duration is calculated before saving")
        return True
    else:
        print("❌ Some validation handlers do not properly save post_log")
        return False


if __name__ == '__main__':
    import sys
    success = test_postlog_save_in_validation_errors()
    print("\n" + "="*70)
    sys.exit(0 if success else 1)
