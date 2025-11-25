# -*- coding: utf-8 -*-
"""
Authentication middleware for Supabase JWT tokens
"""

from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin
from .utils import verify_supabase_token, extract_token_from_header

User = get_user_model()


class SupabaseAuthMiddleware(MiddlewareMixin):
    """
    Middleware to authenticate requests using Supabase JWT tokens.
    
    This middleware supplements Django's standard session-based authentication.
    It only processes JWT tokens and does NOT override existing session-based
    authentication when no JWT token is present.
    """

    def process_request(self, request):
        """
        Process incoming request and authenticate user if valid JWT token is present.
        
        Important: This middleware does NOT override existing session authentication.
        If the user is already authenticated via session, or if no JWT token is present,
        the existing request.user is preserved.

        Args:
            request: Django request object
        """
        # If user is already authenticated via session, skip JWT processing
        # This allows standard Django session-based login to work normally
        if hasattr(request, 'user') and request.user.is_authenticated:
            return None
        
        # Get Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        # Extract token from header
        token = extract_token_from_header(auth_header)

        # If no token is present, preserve existing request.user (don't override)
        # This is critical for session-based authentication to work
        if not token:
            return None

        # Verify token
        payload = verify_supabase_token(token)

        # If token is invalid, preserve existing request.user
        if not payload:
            return None

        # Extract user ID from payload
        supabase_user_id = payload.get('sub')
        email = payload.get('email')

        # If no supabase_user_id in token, preserve existing request.user
        if not supabase_user_id:
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

        # Attach user to request (JWT authentication successful)
        request.user = user
        return None
