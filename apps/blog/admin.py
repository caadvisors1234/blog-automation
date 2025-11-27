# -*- coding: utf-8 -*-
"""
Django admin configuration for blog app
"""

from django.contrib import admin
from .models import BlogPost, BlogImage, PostLog, SALONBoardAccount


class BlogImageInline(admin.TabularInline):
    """
    Inline admin for BlogImage
    """
    model = BlogImage
    extra = 0
    readonly_fields = ['uploaded_at']
    fields = ['image_file', 'order', 'uploaded_at']


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    """
    Admin interface for BlogPost model
    """
    list_display = [
        'id',
        'title',
        'user',
        'status',
        'ai_generated',
        'image_count',
        'stylist_id',
        'published_at',
        'created_at',
    ]
    list_filter = [
        'status',
        'ai_generated',
        'created_at',
        'published_at',
    ]
    search_fields = [
        'title',
        'content',
        'user__username',
        'user__email',
        'stylist_id',
        'coupon_name',
    ]
    readonly_fields = [
        'id',
        'generated_content',
        'ai_generated',
        'celery_task_id',
        'salon_board_url',
        'published_at',
        'created_at',
        'updated_at',
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'title', 'content', 'status')
        }),
        ('AI Generation', {
            'fields': ('ai_prompt', 'keywords', 'ai_generated', 'generated_content')
        }),
        ('SALON BOARD Parameters', {
            'fields': ('stylist_id', 'coupon_name')
        }),
        ('SALON BOARD Result', {
            'fields': ('celery_task_id', 'salon_board_url', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [BlogImageInline]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    def image_count(self, obj):
        """Get image count for display"""
        return obj.images.count()
    image_count.short_description = 'Images'


@admin.register(BlogImage)
class BlogImageAdmin(admin.ModelAdmin):
    """
    Admin interface for BlogImage model
    """
    list_display = [
        'id',
        'blog_post',
        'order',
        'uploaded_at',
    ]
    list_filter = [
        'uploaded_at',
    ]
    search_fields = [
        'blog_post__title',
        'blog_post__user__username',
    ]
    readonly_fields = [
        'id',
        'uploaded_at',
    ]
    ordering = ['blog_post', 'order']


@admin.register(PostLog)
class PostLogAdmin(admin.ModelAdmin):
    """
    Admin interface for PostLog model
    """
    list_display = [
        'id',
        'user',
        'blog_post',
        'status',
        'duration_seconds',
        'started_at',
        'completed_at',
    ]
    list_filter = [
        'status',
        'started_at',
        'completed_at',
    ]
    search_fields = [
        'user__username',
        'blog_post__title',
        'error_message',
    ]
    readonly_fields = [
        'id',
        'user',
        'blog_post',
        'started_at',
        'completed_at',
        'duration_seconds',
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'blog_post', 'status')
        }),
        ('Error Details', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Record Data', {
            'fields': ('screenshot_path', 'scraping_data', 'duration_seconds')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at'),
        }),
    )
    ordering = ['-started_at']
    date_hierarchy = 'started_at'


@admin.register(SALONBoardAccount)
class SALONBoardAccountAdmin(admin.ModelAdmin):
    """
    Admin interface for SALONBoardAccount model
    """
    list_display = [
        'id',
        'user',
        'login_id',
        'is_active',
        'created_at',
    ]
    list_filter = [
        'is_active',
        'created_at',
    ]
    search_fields = [
        'user__username',
        'user__email',
        'login_id',
    ]
    readonly_fields = [
        'id',
        'encrypted_password',
        'created_at',
        'updated_at',
    ]
    fieldsets = (
        ('Account Information', {
            'fields': ('id', 'user', 'login_id', 'is_active')
        }),
        ('Security', {
            'fields': ('encrypted_password',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
