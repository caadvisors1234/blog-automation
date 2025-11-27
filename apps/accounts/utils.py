# -*- coding: utf-8 -*-
"""
Supabase authentication utilities
"""

import jwt
import logging
from django.conf import settings
from supabase import create_client, Client
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


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
        logger.debug(f'Attempting to verify JWT token with secret length: {len(settings.SUPABASE_JWT_SECRET)}')

        # Decode and verify JWT token
        # Note: We don't verify 'aud' (audience) because Supabase tokens have 'aud': 'authenticated'
        # which is expected for user tokens, but PyJWT requires exact match if we verify it.
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=['HS256'],
            options={
                'verify_signature': True,
                'verify_exp': True,
                'verify_iat': True,
                'verify_aud': False,  # Don't verify audience claim
            }
        )
        logger.info(f'JWT token verified successfully. User ID: {payload.get("sub")}, Email: {payload.get("email")}')
        return payload
    except jwt.ExpiredSignatureError as e:
        logger.error(f'JWT token expired: {str(e)}')
        return None
    except jwt.InvalidTokenError as e:
        logger.error(f'Invalid JWT token: {str(e)}')
        return None
    except Exception as e:
        logger.error(f'Unexpected error verifying JWT token: {str(e)}', exc_info=True)
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
