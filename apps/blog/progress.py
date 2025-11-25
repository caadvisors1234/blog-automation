"""
Progress notification utilities for Celery tasks.

This module provides functions to send real-time progress updates
from Celery tasks to connected WebSocket clients via Django Channels.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


class ProgressNotifier:
    """
    Helper class for sending progress notifications to WebSocket clients.
    
    This class encapsulates the logic for sending various types of
    progress updates to connected clients.
    
    Attributes:
        channel_layer: Django Channels layer instance
        post_id: Blog post ID
        user_id: User ID
        task_type: Type of task (generate/publish)
    """
    
    TASK_TYPE_GENERATE = 'generate'
    TASK_TYPE_PUBLISH = 'publish'
    
    def __init__(
        self,
        post_id: int,
        user_id: int,
        task_type: str,
        task_id: Optional[str] = None
    ):
        """
        Initialize the progress notifier.
        
        Args:
            post_id: Blog post ID
            user_id: User ID
            task_type: Type of task (generate/publish)
            task_id: Optional Celery task ID
        """
        self.channel_layer = get_channel_layer()
        self.post_id = post_id
        self.user_id = user_id
        self.task_type = task_type
        self.task_id = task_id
        
        # Define group names for broadcasting
        self.user_group = f"blog_progress_{user_id}"
        self.post_group = f"blog_progress_post_{post_id}"
        
        if task_id:
            self.task_group = f"celery_task_{task_id}"
        else:
            self.task_group = None
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()
    
    def _send_to_groups(self, event: Dict[str, Any]) -> None:
        """
        Send event to all relevant channel groups.
        
        Args:
            event: Event data to send
        """
        if not self.channel_layer:
            logger.warning("Channel layer not available, skipping notification")
            return
        
        try:
            # Send to user group
            async_to_sync(self.channel_layer.group_send)(
                self.user_group,
                event
            )
            
            # Send to post-specific group
            async_to_sync(self.channel_layer.group_send)(
                self.post_group,
                event
            )
        except Exception as e:
            logger.error(f"Failed to send progress notification: {e}")
    
    def _send_to_task_group(self, event: Dict[str, Any]) -> None:
        """
        Send event to task-specific channel group.
        
        Args:
            event: Event data to send
        """
        if not self.channel_layer or not self.task_group:
            return
        
        try:
            async_to_sync(self.channel_layer.group_send)(
                self.task_group,
                event
            )
        except Exception as e:
            logger.error(f"Failed to send task status notification: {e}")
    
    def send_started(self, message: str = "Task started") -> None:
        """
        Send task started notification.
        
        Args:
            message: Human-readable message
        """
        event = {
            'type': 'task_started',
            'post_id': self.post_id,
            'task_type': self.task_type,
            'task_id': self.task_id,
            'message': message,
            'timestamp': self._get_timestamp(),
        }
        self._send_to_groups(event)
        
        if self.task_group:
            self._send_to_task_group({
                'type': 'task_status',
                'task_id': self.task_id,
                'status': 'STARTED',
                'progress': 0,
                'timestamp': self._get_timestamp(),
            })
        
        logger.info(f"Sent task_started for post {self.post_id}")
    
    def send_progress(
        self,
        progress: int,
        message: str,
        status: str = 'progress'
    ) -> None:
        """
        Send progress update notification.
        
        Args:
            progress: Progress percentage (0-100)
            message: Human-readable status message
            status: Status string (progress/processing/etc.)
        """
        event = {
            'type': 'task_progress',
            'post_id': self.post_id,
            'task_type': self.task_type,
            'progress': min(max(progress, 0), 100),  # Clamp to 0-100
            'message': message,
            'status': status,
            'timestamp': self._get_timestamp(),
        }
        self._send_to_groups(event)
        
        if self.task_group:
            self._send_to_task_group({
                'type': 'task_status',
                'task_id': self.task_id,
                'status': 'PROGRESS',
                'progress': progress,
                'timestamp': self._get_timestamp(),
            })
        
        logger.debug(f"Sent progress {progress}% for post {self.post_id}: {message}")
    
    def send_completed(
        self,
        result: Optional[Dict[str, Any]] = None,
        message: str = "Task completed successfully"
    ) -> None:
        """
        Send task completion notification.
        
        Args:
            result: Task result data
            message: Human-readable message
        """
        event = {
            'type': 'task_completed',
            'post_id': self.post_id,
            'task_type': self.task_type,
            'result': result or {},
            'message': message,
            'timestamp': self._get_timestamp(),
        }
        self._send_to_groups(event)
        
        if self.task_group:
            self._send_to_task_group({
                'type': 'task_status',
                'task_id': self.task_id,
                'status': 'SUCCESS',
                'result': result,
                'progress': 100,
                'timestamp': self._get_timestamp(),
            })
        
        logger.info(f"Sent task_completed for post {self.post_id}")
    
    def send_failed(
        self,
        error: str,
        message: str = "Task failed",
        retry_count: int = 0
    ) -> None:
        """
        Send task failure notification.
        
        Args:
            error: Error message or description
            message: Human-readable message
            retry_count: Number of retry attempts
        """
        event = {
            'type': 'task_failed',
            'post_id': self.post_id,
            'task_type': self.task_type,
            'error': error,
            'message': message,
            'retry_count': retry_count,
            'timestamp': self._get_timestamp(),
        }
        self._send_to_groups(event)
        
        if self.task_group:
            self._send_to_task_group({
                'type': 'task_status',
                'task_id': self.task_id,
                'status': 'FAILURE',
                'result': {'error': error},
                'timestamp': self._get_timestamp(),
            })
        
        logger.info(f"Sent task_failed for post {self.post_id}: {error}")
    
    def send_status_update(
        self,
        old_status: str,
        new_status: str,
        message: str = ""
    ) -> None:
        """
        Send blog post status update notification.
        
        Args:
            old_status: Previous status
            new_status: New status
            message: Optional message
        """
        event = {
            'type': 'status_update',
            'post_id': self.post_id,
            'old_status': old_status,
            'new_status': new_status,
            'message': message or f"Status changed: {old_status} → {new_status}",
            'timestamp': self._get_timestamp(),
        }
        self._send_to_groups(event)
        
        logger.info(f"Sent status_update for post {self.post_id}: {old_status} → {new_status}")


# =============================================================================
# Convenience functions for quick notifications
# =============================================================================

def send_progress(
    post_id: int,
    user_id: int,
    task_type: str,
    progress: int,
    message: str,
    task_id: Optional[str] = None
) -> None:
    """
    Send a progress notification.
    
    Convenience function for sending progress updates without
    creating a ProgressNotifier instance.
    
    Args:
        post_id: Blog post ID
        user_id: User ID
        task_type: Task type (generate/publish)
        progress: Progress percentage (0-100)
        message: Status message
        task_id: Optional Celery task ID
    """
    notifier = ProgressNotifier(post_id, user_id, task_type, task_id)
    notifier.send_progress(progress, message)


def send_error(
    post_id: int,
    user_id: int,
    task_type: str,
    error: str,
    task_id: Optional[str] = None,
    retry_count: int = 0
) -> None:
    """
    Send an error notification.
    
    Convenience function for sending error notifications without
    creating a ProgressNotifier instance.
    
    Args:
        post_id: Blog post ID
        user_id: User ID
        task_type: Task type (generate/publish)
        error: Error message
        task_id: Optional Celery task ID
        retry_count: Number of retry attempts
    """
    notifier = ProgressNotifier(post_id, user_id, task_type, task_id)
    notifier.send_failed(error, retry_count=retry_count)


def send_status_change(
    post_id: int,
    user_id: int,
    old_status: str,
    new_status: str
) -> None:
    """
    Send a status change notification.
    
    Args:
        post_id: Blog post ID
        user_id: User ID
        old_status: Previous status
        new_status: New status
    """
    notifier = ProgressNotifier(post_id, user_id, 'status')
    notifier.send_status_update(old_status, new_status)

