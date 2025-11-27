# -*- coding: utf-8 -*-
"""
Django admin configuration for accounts app
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import LoginAttempt

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
        'hpb_salon_id',
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
        'hpb_salon_id',
    ]
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Supabase Integration', {
            'fields': ('supabase_user_id',)
        }),
        ('HPB Settings', {
            'fields': ('hpb_salon_url', 'hpb_salon_id')
        }),
    )
    readonly_fields = ['date_joined', 'last_login', 'hpb_salon_id']
    ordering = ['-date_joined']


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """
    Admin interface for LoginAttempt model
    """
    list_display = [
        'timestamp',
        'email',
        'success',
        'ip_address',
        'user',
        'failure_reason',
    ]
    list_filter = [
        'success',
        'timestamp',
    ]
    search_fields = [
        'email',
        'ip_address',
        'user__username',
        'user__email',
    ]
    readonly_fields = [
        'user',
        'email',
        'ip_address',
        'user_agent',
        'success',
        'failure_reason',
        'timestamp',
    ]
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        """Disable manual creation of login attempts"""
        return False

    def has_change_permission(self, request, obj=None):
        """Make login attempts read-only"""
        return False
