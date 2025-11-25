# -*- coding: utf-8 -*-
"""
Django admin configuration for blog app
"""

from django.contrib import admin
from .models import BlogPost, SALONBoardAccount


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
    ]
    readonly_fields = [
        'id',
        'ai_generated',
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
            'fields': ('ai_prompt', 'ai_generated')
        }),
        ('SALON BOARD', {
            'fields': ('salon_board_url', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    date_hierarchy = 'created_at'


@admin.register(SALONBoardAccount)
class SALONBoardAccountAdmin(admin.ModelAdmin):
    """
    Admin interface for SALONBoardAccount model
    """
    list_display = [
        'id',
        'user',
        'email',
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
        'email',
    ]
    readonly_fields = [
        'id',
        'encrypted_password',
        'created_at',
        'updated_at',
    ]
    fieldsets = (
        ('Account Information', {
            'fields': ('id', 'user', 'email', 'is_active')
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
