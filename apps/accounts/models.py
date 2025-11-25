# -*- coding: utf-8 -*-
"""
User authentication models
"""

import re
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for Supabase integration and HPB settings
    """
    # Supabase integration fields
    supabase_user_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Supabase User ID',
        help_text='User ID from Supabase authentication system'
    )

    # HPB (Hot Pepper Beauty) settings
    hpb_salon_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='HPB Salon URL',
        help_text='HPB salon top page URL (e.g., https://beauty.hotpepper.jp/slnH000xxxxx/)'
    )
    hpb_salon_id = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        verbose_name='HPB Salon ID',
        help_text='Extracted salon ID (e.g., H000123456)'
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'accounts_user'
        indexes = [
            models.Index(fields=['supabase_user_id']),
            models.Index(fields=['hpb_salon_id']),
            models.Index(fields=['date_joined']),
        ]

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        """
        Override save to extract salon ID from HPB URL
        """
        if self.hpb_salon_url and not self.hpb_salon_id:
            self.hpb_salon_id = self._extract_salon_id(self.hpb_salon_url)
        super().save(*args, **kwargs)

    @staticmethod
    def _extract_salon_id(url: str) -> str:
        """
        Extract salon ID from HPB URL

        Args:
            url: HPB salon URL

        Returns:
            Salon ID (e.g., H000123456) or empty string
        """
        if not url:
            return ''
        # Match patterns like slnH000123456 or slnH000123456
        match = re.search(r'sln(H\d+)', url)
        if match:
            return match.group(1)
        return ''
