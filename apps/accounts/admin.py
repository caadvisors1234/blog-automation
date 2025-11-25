# -*- coding: utf-8 -*-
"""
Django admin configuration for accounts app
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin interface for custom User model
    """
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'is_active',
        'date_joined',
    ]
    list_filter = [
        'is_staff',
        'is_superuser',
        'is_active',
        'date_joined',
    ]
    search_fields = [
        'username',
        'email',
        'first_name',
        'last_name',
        'supabase_user_id',
    ]
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Supabase Integration', {
            'fields': ('supabase_user_id',)
        }),
    )
    readonly_fields = ['date_joined', 'last_login']
    ordering = ['-date_joined']
