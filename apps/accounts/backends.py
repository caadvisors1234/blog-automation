# -*- coding: utf-8 -*-
"""
Supabase authentication backend
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class SupabaseAuthBackend(ModelBackend):
    """
    Supabase authentication backend

    Validates Supabase tokens and syncs with Django users.
    """

    def authenticate(self, request, supabase_user_id=None, email=None, **kwargs):
        """
        Authenticate user by Supabase User ID or email
        """
        if supabase_user_id:
            try:
                user = User.objects.get(supabase_user_id=supabase_user_id)
                return user
            except User.DoesNotExist:
                return None

        if email:
            try:
                user = User.objects.get(email=email)
                return user
            except User.DoesNotExist:
                return None

        return None
