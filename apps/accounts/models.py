# -*- coding: utf-8 -*-
"""
User authentication models
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for Supabase integration
    """
    # Supabase integration fields
    supabase_user_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Supabase User ID',
        help_text='User ID from Supabase authentication system'
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'accounts_user'

    def __str__(self):
        return self.username
