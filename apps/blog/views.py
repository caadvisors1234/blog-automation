# -*- coding: utf-8 -*-
"""
Blog post management views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import BlogPost
from .serializers import (
    BlogPostListSerializer,
    BlogPostDetailSerializer,
    BlogPostCreateSerializer,
    BlogPostUpdateSerializer,
)


class BlogPostViewSet(viewsets.ModelViewSet):
    """
    Blog post management viewset

    Provides endpoints for:
    - GET /api/blog/posts/ - List user's blog posts
    - POST /api/blog/posts/ - Create new blog post
    - GET /api/blog/posts/{id}/ - Get specific post
    - PATCH /api/blog/posts/{id}/ - Update post
    - DELETE /api/blog/posts/{id}/ - Delete post
    - POST /api/blog/posts/{id}/generate/ - Trigger AI generation
    - POST /api/blog/posts/{id}/publish/ - Trigger SALON BOARD publishing
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Get blog posts for current user

        Returns:
            QuerySet of user's blog posts
        """
        queryset = BlogPost.objects.filter(user=self.request.user)

        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by AI-generated
        ai_generated = self.request.query_params.get('ai_generated')
        if ai_generated is not None:
            ai_generated_bool = ai_generated.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(ai_generated=ai_generated_bool)

        # Search by title
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action

        Returns:
            Serializer class
        """
        if self.action == 'list':
            return BlogPostListSerializer
        elif self.action == 'create':
            return BlogPostCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return BlogPostUpdateSerializer
        else:
            return BlogPostDetailSerializer

    def perform_create(self, serializer):
        """
        Create blog post for current user

        Args:
            serializer: Validated serializer instance
        """
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='generate')
    def generate(self, request, pk=None):
        """
        Trigger AI content generation for blog post

        Args:
            request: HTTP request
            pk: Blog post ID

        Returns:
            Response with task information
        """
        blog_post = self.get_object()

        # Validate that post can be generated
        if blog_post.status not in ['draft', 'failed']:
            return Response(
                {'detail': 'Post must be in draft or failed status to generate'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not blog_post.ai_prompt:
            return Response(
                {'detail': 'AI prompt is required for generation'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status to generating
        blog_post.status = 'generating'
        blog_post.save(update_fields=['status'])

        # Import here to avoid circular imports
        from .tasks import generate_blog_content_task

        # Trigger Celery task
        task = generate_blog_content_task.delay(blog_post.id)

        return Response({
            'detail': 'AI content generation started',
            'task_id': task.id,
            'post_id': blog_post.id,
            'status': blog_post.status,
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        """
        Trigger SALON BOARD publishing for blog post

        Args:
            request: HTTP request
            pk: Blog post ID

        Returns:
            Response with task information
        """
        blog_post = self.get_object()

        # Validate that post can be published
        if blog_post.status not in ['ready', 'failed']:
            return Response(
                {'detail': 'Post must be in ready or failed status to publish'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not blog_post.title or not blog_post.content:
            return Response(
                {'detail': 'Title and content are required for publishing'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user has SALON BOARD account
        if not hasattr(request.user, 'salon_board_account'):
            return Response(
                {'detail': 'SALON BOARD account is required for publishing'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not request.user.salon_board_account.is_active:
            return Response(
                {'detail': 'SALON BOARD account is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status to publishing
        blog_post.status = 'publishing'
        blog_post.save(update_fields=['status'])

        # Import here to avoid circular imports
        from .tasks import publish_to_salon_board_task

        # Trigger Celery task
        task = publish_to_salon_board_task.delay(blog_post.id)

        return Response({
            'detail': 'SALON BOARD publishing started',
            'task_id': task.id,
            'post_id': blog_post.id,
            'status': blog_post.status,
        }, status=status.HTTP_202_ACCEPTED)
