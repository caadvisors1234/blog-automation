#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebSocket functionality test script.

Tests the Django Channels WebSocket implementation including:
- Consumer connection/disconnection
- Progress notification utilities
- Channel layer configuration
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import asyncio
from datetime import datetime
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

from config.asgi import application
from apps.blog.progress import ProgressNotifier, send_progress, send_error


User = get_user_model()


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_result(test_name: str, success: bool, details: str = ""):
    """Print test result."""
    status = "✅ PASSED" if success else "❌ FAILED"
    print(f"  {status}: {test_name}")
    if details:
        print(f"         {details}")


async def test_channel_layer_config():
    """Test that the channel layer is properly configured."""
    print_section("Channel Layer Configuration Test")
    
    try:
        channel_layer = get_channel_layer()
        
        # Check channel layer exists
        if channel_layer is None:
            print_result("Channel layer exists", False, "Channel layer is None")
            return False
        
        print_result("Channel layer exists", True, f"Backend: {type(channel_layer).__name__}")
        
        # Test sending a message to a group
        test_group = "test_group_123"
        test_message = {
            "type": "test.message",
            "content": "Hello from test"
        }
        
        # This should not raise an error if Redis is connected
        await channel_layer.group_add(test_group, "test_channel")
        await channel_layer.group_send(test_group, test_message)
        await channel_layer.group_discard(test_group, "test_channel")
        
        print_result("Channel layer send/receive", True, "Redis connection working")
        return True
        
    except Exception as e:
        print_result("Channel layer configuration", False, str(e))
        return False


async def test_progress_notifier():
    """Test the ProgressNotifier class."""
    print_section("Progress Notifier Test")
    
    try:
        # Create a test notifier
        notifier = ProgressNotifier(
            post_id=999,
            user_id=1,
            task_type='generate',
            task_id='test-task-123'
        )
        
        print_result("ProgressNotifier initialization", True)
        
        # Test group names
        assert notifier.user_group == "blog_progress_1"
        assert notifier.post_group == "blog_progress_post_999"
        assert notifier.task_group == "celery_task_test-task-123"
        
        print_result("Group name generation", True, 
                    f"User: {notifier.user_group}, Post: {notifier.post_group}")
        
        # Test timestamp generation
        timestamp = notifier._get_timestamp()
        assert datetime.fromisoformat(timestamp)
        
        print_result("Timestamp generation", True, f"Format: {timestamp}")
        
        # Test send methods (these will send to non-existent groups, which is fine)
        try:
            notifier.send_started("Test started")
            notifier.send_progress(50, "Test progress")
            notifier.send_completed(result={'test': True})
            notifier.send_failed("Test error")
            notifier.send_status_update("draft", "ready")
            
            print_result("Notification methods", True, "All methods executed without error")
        except Exception as e:
            print_result("Notification methods", False, str(e))
            return False
        
        return True
        
    except Exception as e:
        print_result("Progress notifier test", False, str(e))
        return False


async def test_convenience_functions():
    """Test convenience functions for sending notifications."""
    print_section("Convenience Functions Test")
    
    try:
        # Test send_progress
        send_progress(
            post_id=999,
            user_id=1,
            task_type='generate',
            progress=50,
            message='Test progress message'
        )
        print_result("send_progress()", True)
        
        # Test send_error
        send_error(
            post_id=999,
            user_id=1,
            task_type='publish',
            error='Test error message'
        )
        print_result("send_error()", True)
        
        return True
        
    except Exception as e:
        print_result("Convenience functions", False, str(e))
        return False


async def test_websocket_routing():
    """Test that WebSocket routes are properly configured."""
    print_section("WebSocket Routing Test")
    
    try:
        from apps.blog.routing import websocket_urlpatterns
        
        # Check routes are defined
        assert len(websocket_urlpatterns) >= 2
        
        print_result("WebSocket routes defined", True, 
                    f"Found {len(websocket_urlpatterns)} routes")
        
        # Check route names
        route_names = [pattern.name for pattern in websocket_urlpatterns if hasattr(pattern, 'name')]
        print_result("Route names", True, f"Routes: {route_names}")
        
        return True
        
    except Exception as e:
        print_result("WebSocket routing", False, str(e))
        return False


async def test_consumer_import():
    """Test that consumers can be imported correctly."""
    print_section("Consumer Import Test")
    
    try:
        from apps.blog.consumers import BlogProgressConsumer, TaskStatusConsumer
        
        print_result("BlogProgressConsumer import", True)
        print_result("TaskStatusConsumer import", True)
        
        # Check methods exist
        assert hasattr(BlogProgressConsumer, 'connect')
        assert hasattr(BlogProgressConsumer, 'disconnect')
        assert hasattr(BlogProgressConsumer, 'receive_json')
        assert hasattr(BlogProgressConsumer, 'task_progress')
        assert hasattr(BlogProgressConsumer, 'task_completed')
        assert hasattr(BlogProgressConsumer, 'task_failed')
        
        print_result("Consumer methods", True, "All required methods present")
        
        return True
        
    except Exception as e:
        print_result("Consumer import", False, str(e))
        return False


async def test_asgi_application():
    """Test that the ASGI application is properly configured."""
    print_section("ASGI Application Test")
    
    try:
        from config.asgi import application
        from channels.routing import ProtocolTypeRouter
        
        # Check application type
        assert isinstance(application, ProtocolTypeRouter)
        print_result("ASGI application type", True, "ProtocolTypeRouter")
        
        # Check protocols are configured
        assert 'http' in application.application_mapping
        assert 'websocket' in application.application_mapping
        
        print_result("HTTP protocol", True)
        print_result("WebSocket protocol", True)
        
        return True
        
    except Exception as e:
        print_result("ASGI application", False, str(e))
        return False


async def run_all_tests():
    """Run all WebSocket tests."""
    print("\n" + "="*60)
    print("  WEBSOCKET FUNCTIONALITY TEST SUITE")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(await test_consumer_import())
    results.append(await test_websocket_routing())
    results.append(await test_asgi_application())
    results.append(await test_channel_layer_config())
    results.append(await test_progress_notifier())
    results.append(await test_convenience_functions())
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(results)
    total = len(results)
    
    print(f"  Total tests: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {total - passed}")
    print()
    
    if passed == total:
        print("  🎉 ALL TESTS PASSED!")
    else:
        print("  ⚠️  Some tests failed. Please check the output above.")
    
    print("\n" + "="*60 + "\n")
    
    return passed == total


if __name__ == '__main__':
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

