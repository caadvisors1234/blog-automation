"""
WebSocket consumers for real-time blog progress updates.

This module provides WebSocket consumers that allow clients to receive
real-time updates about blog post generation and publishing progress.
"""

import json
import logging
from typing import Optional
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class BlogProgressConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for blog post progress updates.
    
    Clients connect to receive real-time updates about:
    - AI content generation progress
    - SALON BOARD publishing progress
    - Task status changes
    - Error notifications
    
    Group naming convention:
    - blog_progress_{user_id} - User-specific updates
    - blog_progress_post_{post_id} - Post-specific updates
    """
    
    async def connect(self):
        """
        Handle WebSocket connection.
        
        Validates user authentication and joins appropriate channel groups.
        """
        self.user = self.scope.get('user')
        self.post_id: Optional[int] = None
        
        # Check if user is authenticated
        if not self.user or not self.user.is_authenticated:
            logger.warning("Unauthenticated WebSocket connection attempt")
            await self.close(code=4001)
            return
        
        # Get post_id from URL if provided
        self.post_id = self.scope['url_route']['kwargs'].get('post_id')
        
        # Join post-specific group if post_id is provided
        if self.post_id:
            # Verify user owns the post before subscribing
            if not await self._user_owns_post(self.post_id):
                logger.warning(
                    "User %s attempted to subscribe to unauthorized post %s",
                    self.user.id,
                    self.post_id,
                )
                await self.close(code=4003)
                return

            self.post_group_name = f"blog_progress_post_{self.post_id}"
            await self.channel_layer.group_add(
                self.post_group_name,
                self.channel_name
            )
            logger.info(f"User {self.user.id} connected to post {self.post_id} progress channel")
        else:
            # Join user-specific group only for general progress channel
            self.user_group_name = f"blog_progress_{self.user.id}"
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            self.post_group_name = None
            logger.info(f"User {self.user.id} connected to general progress channel")
        
        await self.accept()
        
        # Send connection confirmation
        await self.send_json({
            'type': 'connection_established',
            'message': 'Connected to blog progress updates',
            'user_id': self.user.id,
            'post_id': self.post_id,
        })
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        
        Leaves all channel groups and logs the disconnection.
        
        Args:
            close_code: WebSocket close code
        """
        # Leave user group
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        
        # Leave post group if applicable
        if hasattr(self, 'post_group_name') and self.post_group_name:
            await self.channel_layer.group_discard(
                self.post_group_name,
                self.channel_name
            )
        
        logger.info(f"WebSocket disconnected with code {close_code}")
    
    async def receive_json(self, content):
        """
        Handle incoming JSON messages from the client.
        
        Currently supports:
        - ping: Keepalive check
        - subscribe_post: Subscribe to specific post updates
        - unsubscribe_post: Unsubscribe from post updates
        
        Args:
            content: JSON message content
        """
        message_type = content.get('type', '')
        
        if message_type == 'ping':
            # Respond to keepalive ping
            await self.send_json({
                'type': 'pong',
                'timestamp': content.get('timestamp'),
            })
        
        elif message_type == 'subscribe_post':
            # Subscribe to a specific post's updates
            post_id = content.get('post_id')
            if post_id:
                # Verify user owns the post
                if await self._user_owns_post(post_id):
                    new_group = f"blog_progress_post_{post_id}"
                    await self.channel_layer.group_add(
                        new_group,
                        self.channel_name
                    )
                    self.post_id = post_id
                    self.post_group_name = new_group
                    await self.send_json({
                        'type': 'subscribed',
                        'post_id': post_id,
                    })
                else:
                    await self.send_json({
                        'type': 'error',
                        'message': 'Permission denied for this post',
                    })
        
        elif message_type == 'unsubscribe_post':
            # Unsubscribe from post updates
            if self.post_group_name:
                await self.channel_layer.group_discard(
                    self.post_group_name,
                    self.channel_name
                )
                self.post_group_name = None
                self.post_id = None
                await self.send_json({
                    'type': 'unsubscribed',
                })
    
    @database_sync_to_async
    def _user_owns_post(self, post_id: int) -> bool:
        """
        Check if the connected user owns the specified post.
        
        Args:
            post_id: Blog post ID to check
            
        Returns:
            True if user owns the post, False otherwise
        """
        from apps.blog.models import BlogPost
        return BlogPost.objects.filter(id=post_id, user=self.user).exists()
    
    # ============================================
    # Event Handlers (called by channel_layer.group_send)
    # ============================================
    
    async def task_progress(self, event):
        """
        Handle task progress update events.
        
        Sends progress information to the connected client.
        
        Args:
            event: Event data containing progress information
                - post_id: Blog post ID
                - task_type: Type of task (generate/publish)
                - progress: Progress percentage (0-100)
                - message: Human-readable status message
                - status: Task status (pending/started/progress/success/failed)
        """
        await self.send_json({
            'type': 'task_progress',
            'post_id': event.get('post_id'),
            'task_type': event.get('task_type'),
            'progress': event.get('progress', 0),
            'message': event.get('message', ''),
            'status': event.get('status', 'progress'),
            'timestamp': event.get('timestamp'),
        })
    
    async def task_started(self, event):
        """
        Handle task started events.
        
        Args:
            event: Event data containing task start information
        """
        await self.send_json({
            'type': 'task_started',
            'post_id': event.get('post_id'),
            'task_type': event.get('task_type'),
            'task_id': event.get('task_id'),
            'message': event.get('message', 'Task started'),
            'timestamp': event.get('timestamp'),
        })
    
    async def task_completed(self, event):
        """
        Handle task completion events.
        
        Args:
            event: Event data containing completion information
        """
        await self.send_json({
            'type': 'task_completed',
            'post_id': event.get('post_id'),
            'task_type': event.get('task_type'),
            'result': event.get('result', {}),
            'message': event.get('message', 'Task completed'),
            'timestamp': event.get('timestamp'),
        })
    
    async def task_failed(self, event):
        """
        Handle task failure events.
        
        Args:
            event: Event data containing error information
        """
        await self.send_json({
            'type': 'task_failed',
            'post_id': event.get('post_id'),
            'task_type': event.get('task_type'),
            'error': event.get('error', 'Unknown error'),
            'message': event.get('message', 'Task failed'),
            'retry_count': event.get('retry_count', 0),
            'timestamp': event.get('timestamp'),
        })
    
    async def status_update(self, event):
        """
        Handle blog post status update events.
        
        Args:
            event: Event data containing status update information
        """
        await self.send_json({
            'type': 'status_update',
            'post_id': event.get('post_id'),
            'old_status': event.get('old_status'),
            'new_status': event.get('new_status'),
            'message': event.get('message', ''),
            'timestamp': event.get('timestamp'),
        })


class TaskStatusConsumer(AsyncJsonWebsocketConsumer):
    """
    Simple WebSocket consumer for monitoring Celery task status.
    
    This consumer allows clients to subscribe to specific task IDs
    and receive status updates.
    """
    
    async def connect(self):
        """Handle WebSocket connection for task monitoring."""
        self.user = self.scope.get('user')
        self.task_id = self.scope['url_route']['kwargs'].get('task_id')
        
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        if not self.task_id:
            await self.close(code=4000)
            return

        # Verify user is authorized to view this task
        if not await self._user_owns_task(self.task_id):
            logger.warning(
                "User %s attempted to subscribe to unauthorized task %s",
                self.user.id,
                self.task_id,
            )
            await self.close(code=4003)
            return
        
        self.task_group_name = f"celery_task_{self.task_id}"
        
        await self.channel_layer.group_add(
            self.task_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send_json({
            'type': 'connection_established',
            'task_id': self.task_id,
        })
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'task_group_name'):
            await self.channel_layer.group_discard(
                self.task_group_name,
                self.channel_name
            )

    @database_sync_to_async
    def _user_owns_task(self, task_id: str) -> bool:
        """
        Check if the connected user owns the specified task.

        Args:
            task_id: Celery task ID to check

        Returns:
            True if user owns a post with the task_id, False otherwise
        """
        from apps.blog.models import BlogPost
        return BlogPost.objects.filter(
            user=self.user,
            celery_task_id=task_id
        ).exists()
    
    async def task_status(self, event):
        """
        Handle task status update events.
        
        Args:
            event: Event data containing task status
        """
        await self.send_json({
            'type': 'task_status',
            'task_id': event.get('task_id'),
            'status': event.get('status'),
            'result': event.get('result'),
            'progress': event.get('progress'),
            'timestamp': event.get('timestamp'),
        })

