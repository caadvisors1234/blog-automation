"""
WebSocket URL routing for blog app.

This module defines WebSocket URL patterns for real-time communication.
"""

from django.urls import path, re_path
from . import consumers

websocket_urlpatterns = [
    # Blog progress updates - General (user-level)
    path(
        'ws/blog/progress/',
        consumers.BlogProgressConsumer.as_asgi(),
        name='blog_progress'
    ),
    
    # Blog progress updates - Post-specific
    path(
        'ws/blog/progress/<int:post_id>/',
        consumers.BlogProgressConsumer.as_asgi(),
        name='blog_progress_post'
    ),
    
    # Celery task status monitoring
    re_path(
        r'ws/task/(?P<task_id>[\w-]+)/$',
        consumers.TaskStatusConsumer.as_asgi(),
        name='task_status'
    ),
]
