# -*- coding: utf-8 -*-
"""
Supabase authentication utilities
"""

import jwt
from django.conf import settings
from supabase import create_client, Client
from typing import Optional, Dict, Any


def get_supabase_client() -> Client:
    """
    Get Supabase client instance

    Returns:
        Supabase client
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def get_supabase_admin_client() -> Client:
    """
    Get Supabase admin client with service role key

    Returns:
        Supabase admin client
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def verify_supabase_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify Supabase JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        # Decode and verify JWT token
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=['HS256'],
            options={
                'verify_signature': True,
                'verify_exp': True,
                'verify_iat': True,
            }
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None


def extract_token_from_header(auth_header: str) -> Optional[str]:
    """
    Extract JWT token from Authorization header

    Args:
        auth_header: Authorization header value (e.g., "Bearer <token>")

    Returns:
        Token string if valid format, None otherwise
    """
    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None

    return parts[1]
