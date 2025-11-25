# -*- coding: utf-8 -*-
"""
Serializers for blog posts
"""

from rest_framework import serializers
from .models import BlogPost
from django.contrib.auth import get_user_model

User = get_user_model()


class BlogPostListSerializer(serializers.ModelSerializer):
    """
    Serializer for blog post list view
    """
    author_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            'id',
            'title',
            'status',
            'ai_generated',
            'author_name',
            'published_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]


class BlogPostDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for blog post detail view
    """
    author_name = serializers.CharField(source='user.username', read_only=True)
    author_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            'id',
            'title',
            'content',
            'status',
            'ai_prompt',
            'ai_generated',
            'salon_board_url',
            'published_at',
            'author_name',
            'author_email',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'ai_generated',
            'salon_board_url',
            'published_at',
            'created_at',
            'updated_at',
        ]


class BlogPostCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating blog posts
    """

    class Meta:
        model = BlogPost
        fields = [
            'title',
            'content',
            'ai_prompt',
        ]

    def create(self, validated_data):
        """
        Create blog post

        Args:
            validated_data: Validated data from request

        Returns:
            Created BlogPost instance
        """
        user = self.context['request'].user

        # Determine if AI-generated based on ai_prompt
        ai_generated = bool(validated_data.get('ai_prompt'))

        blog_post = BlogPost.objects.create(
            user=user,
            title=validated_data.get('title', ''),
            content=validated_data.get('content', ''),
            ai_prompt=validated_data.get('ai_prompt', ''),
            ai_generated=ai_generated,
            status='draft'
        )

        return blog_post


class BlogPostUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating blog posts
    """

    class Meta:
        model = BlogPost
        fields = [
            'title',
            'content',
            'status',
        ]

    def validate_status(self, value):
        """
        Validate status transitions

        Args:
            value: New status value

        Returns:
            Validated status

        Raises:
            ValidationError: If status transition is invalid
        """
        instance = self.instance
        if not instance:
            return value

        current_status = instance.status

        # Define valid status transitions
        valid_transitions = {
            'draft': ['generating', 'ready', 'failed'],
            'generating': ['ready', 'failed', 'draft'],
            'ready': ['publishing', 'draft'],
            'publishing': ['published', 'failed'],
            'published': [],  # Cannot change from published
            'failed': ['draft', 'generating'],
        }

        # Check if transition is valid
        if current_status == 'published':
            raise serializers.ValidationError(
                'Cannot change status of published posts'
            )

        if value not in valid_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f'Invalid status transition from {current_status} to {value}'
            )

        return value
