# -*- coding: utf-8 -*-
"""
Authentication middleware for Supabase JWT tokens
"""

from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from .utils import verify_supabase_token, extract_token_from_header

User = get_user_model()


class SupabaseAuthMiddleware(MiddlewareMixin):
    """
    Middleware to authenticate requests using Supabase JWT tokens
    """

    def process_request(self, request):
        """
        Process incoming request and authenticate user if valid JWT token is present

        Args:
            request: Django request object
        """
        # Get Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        # Extract token from header
        token = extract_token_from_header(auth_header)

        if not token:
            request.user = AnonymousUser()
            return None

        # Verify token
        payload = verify_supabase_token(token)

        if not payload:
            request.user = AnonymousUser()
            return None

        # Extract user ID from payload
        supabase_user_id = payload.get('sub')
        email = payload.get('email')

        if not supabase_user_id:
            request.user = AnonymousUser()
            return None

        # Try to get or create user
        try:
            user = User.objects.get(supabase_user_id=supabase_user_id)
        except User.DoesNotExist:
            # Create new user from Supabase data
            username = email.split('@')[0] if email else f'user_{supabase_user_id[:8]}'
            user = User.objects.create(
                username=username,
                email=email or '',
                supabase_user_id=supabase_user_id
            )

        # Attach user to request
        request.user = user
        return None
