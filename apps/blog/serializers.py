# -*- coding: utf-8 -*-
"""
Serializers for blog posts
"""

from rest_framework import serializers
from .models import BlogPost, BlogImage, PostLog
from django.contrib.auth import get_user_model

User = get_user_model()

# Constants
MAX_TITLE_LENGTH = 25
MAX_IMAGES_PER_POST = 4


class BlogImageSerializer(serializers.ModelSerializer):
    """
    Serializer for blog images
    """
    image_url = serializers.ReadOnlyField()

    class Meta:
        model = BlogImage
        fields = [
            'id',
            'image_file',
            'image_url',
            'order',
            'uploaded_at',
        ]
        read_only_fields = [
            'id',
            'uploaded_at',
        ]


class BlogPostListSerializer(serializers.ModelSerializer):
    """
    Serializer for blog post list view
    """
    author_name = serializers.CharField(source='user.username', read_only=True)
    image_count = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            'id',
            'title',
            'status',
            'ai_generated',
            'author_name',
            'image_count',
            'stylist_id',
            'coupon_name',
            'published_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]

    def get_image_count(self, obj):
        """Get number of attached images"""
        return obj.images.count()


class BlogPostDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for blog post detail view
    """
    author_name = serializers.CharField(source='user.username', read_only=True)
    author_email = serializers.EmailField(source='user.email', read_only=True)
    images = BlogImageSerializer(many=True, read_only=True)
    log = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            'id',
            'title',
            'content',
            'generated_content',
            'status',
            'ai_prompt',
            'tone',
            'keywords',
            'ai_generated',
            'stylist_id',
            'coupon_name',
            'celery_task_id',
            'salon_board_url',
            'published_at',
            'author_name',
            'author_email',
            'images',
            'log',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'generated_content',
            'ai_generated',
            'celery_task_id',
            'salon_board_url',
            'published_at',
            'created_at',
            'updated_at',
        ]

    def get_log(self, obj):
        """Get post log if exists"""
        try:
            log = obj.log
            return {
                'status': log.status,
                'error_message': log.error_message,
                'screenshot_path': log.screenshot_path,
                'duration_seconds': log.duration_seconds,
                'started_at': log.started_at,
                'completed_at': log.completed_at,
            }
        except PostLog.DoesNotExist:
            return None


class BlogPostCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating blog posts
    """
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=MAX_IMAGES_PER_POST,
        help_text=f'Up to {MAX_IMAGES_PER_POST} images'
    )

    class Meta:
        model = BlogPost
        fields = [
            'title',
            'content',
            'ai_prompt',
            'tone',
            'keywords',
            'stylist_id',
            'coupon_name',
            'images',
        ]

    def validate_title(self, value):
        """Validate title length"""
        if len(value) > MAX_TITLE_LENGTH:
            raise serializers.ValidationError(f'Title must be {MAX_TITLE_LENGTH} characters or less')
        return value

    def validate_images(self, value):
        """Validate image count"""
        if len(value) > MAX_IMAGES_PER_POST:
            raise serializers.ValidationError(f'Maximum {MAX_IMAGES_PER_POST} images allowed')
        return value

    def create(self, validated_data):
        """
        Create blog post with images

        Args:
            validated_data: Validated data from request
                          (user is passed from perform_create via serializer.save(user=...))

        Returns:
            Created BlogPost instance
        """
        images_data = validated_data.pop('images', [])
        
        # user is passed from ViewSet.perform_create()
        # Do not set it here to avoid duplicate assignment

        # Determine if AI-generated based on ai_prompt
        ai_generated = bool(validated_data.get('ai_prompt'))
        
        # Set default status and ai_generated flag
        validated_data['ai_generated'] = ai_generated
        validated_data['status'] = 'draft'

        blog_post = BlogPost.objects.create(**validated_data)

        # Create images
        for idx, image_file in enumerate(images_data):
            BlogImage.objects.create(
                blog_post=blog_post,
                image_file=image_file,
                order=idx
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
            'tone',
            'keywords',
            'stylist_id',
            'coupon_name',
        ]

    def validate_title(self, value):
        """Validate title length"""
        if value and len(value) > MAX_TITLE_LENGTH:
            raise serializers.ValidationError(f'Title must be {MAX_TITLE_LENGTH} characters or less')
        return value

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


class PostLogSerializer(serializers.ModelSerializer):
    """
    Serializer for post logs
    """
    blog_post_title = serializers.CharField(source='blog_post.title', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = PostLog
        fields = [
            'id',
            'blog_post',
            'blog_post_title',
            'user',
            'username',
            'status',
            'error_message',
            'screenshot_path',
            'scraping_data',
            'duration_seconds',
            'started_at',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'blog_post',
            'user',
            'started_at',
            'completed_at',
        ]
