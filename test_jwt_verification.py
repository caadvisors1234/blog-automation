#!/usr/bin/env python
"""
JWT verification test script for debugging Supabase authentication issues
"""

import os
import sys
import django
import jwt
import json
import base64

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings


def decode_jwt_header(token):
    """Decode JWT header without verification to see the algorithm"""
    try:
        # Split token and decode header
        parts = token.split('.')
        if len(parts) != 3:
            print(f"❌ Invalid JWT format. Expected 3 parts, got {len(parts)}")
            return None

        # Decode header (add padding if needed)
        header_b64 = parts[0]
        # Add padding
        header_b64 += '=' * (4 - len(header_b64) % 4)
        header_json = base64.urlsafe_b64decode(header_b64)
        header = json.loads(header_json)

        print("\n📋 JWT Header:")
        print(json.dumps(header, indent=2))

        # Decode payload (without verification)
        payload_b64 = parts[1]
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_json)

        print("\n📋 JWT Payload (unverified):")
        print(json.dumps(payload, indent=2))

        return header

    except Exception as e:
        print(f"❌ Error decoding JWT: {str(e)}")
        return None


def test_jwt_secret():
    """Test JWT secret configuration"""
    print("=" * 80)
    print("🔐 Supabase JWT Verification Test")
    print("=" * 80)

    # Check environment variables
    print("\n1. Checking environment variables...")
    print(f"   SUPABASE_URL: {settings.SUPABASE_URL}")
    print(f"   SUPABASE_KEY: {settings.SUPABASE_KEY[:20]}..." if settings.SUPABASE_KEY else "   SUPABASE_KEY: Not set")
    print(f"   SUPABASE_JWT_SECRET length: {len(settings.SUPABASE_JWT_SECRET)}")
    print(f"   SUPABASE_JWT_SECRET (first 20 chars): {settings.SUPABASE_JWT_SECRET[:20]}...")

    # Ask for a test token
    print("\n2. Please provide a JWT token to test:")
    print("   You can get this by:")
    print("   a) Logging in via browser and checking Network tab")
    print("   b) Using Supabase client: supabase.auth.signInWithPassword()")
    print("   c) Paste the access_token here")
    print()

    token = input("Paste JWT token here (or press Enter to skip): ").strip()

    if not token:
        print("\n⚠️  No token provided. Skipping token verification test.")
        print("\n💡 To get a token, you can:")
        print("   1. Open browser console on login page")
        print("   2. Try to login")
        print("   3. Check Network tab for the response")
        return

    # Decode header to see algorithm
    print("\n3. Decoding JWT header (without verification)...")
    header = decode_jwt_header(token)

    if not header:
        return

    algorithm = header.get('alg', 'UNKNOWN')
    print(f"\n   Algorithm used: {algorithm}")

    # Try to verify with different methods
    print("\n4. Attempting token verification...")

    if algorithm == 'HS256':
        print("   ℹ️  Token uses HS256 (symmetric key)")
        print("   Verifying with SUPABASE_JWT_SECRET...")

        try:
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
            print("   ✅ Token verified successfully with HS256!")
            print(f"   User ID: {payload.get('sub')}")
            print(f"   Email: {payload.get('email')}")

        except jwt.ExpiredSignatureError:
            print("   ❌ Token has expired")
        except jwt.InvalidTokenError as e:
            print(f"   ❌ Token verification failed: {str(e)}")
            print("\n   💡 This might mean:")
            print("      - SUPABASE_JWT_SECRET is incorrect")
            print("      - Token was signed with a different secret")

    elif algorithm in ['RS256', 'ES256']:
        print(f"   ℹ️  Token uses {algorithm} (asymmetric key)")
        print("   This requires fetching public key from Supabase JWKS endpoint")
        print(f"   URL: {settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")
        print("\n   ⚠️  Current implementation uses HS256 only!")
        print("   You need to update verify_supabase_token() to support RS256/ES256")

    else:
        print(f"   ❌ Unknown algorithm: {algorithm}")

    print("\n" + "=" * 80)
    print("📝 Recommendations:")
    print("=" * 80)

    if algorithm == 'HS256':
        print("\n1. Verify your SUPABASE_JWT_SECRET:")
        print("   a) Go to Supabase Dashboard → Project Settings → API")
        print("   b) Find 'JWT Settings' section")
        print("   c) Copy the JWT Secret")
        print("   d) Update your .env file:")
        print(f"      SUPABASE_JWT_SECRET=your-secret-here")
        print("\n2. Make sure to restart the Django server after updating .env")

    elif algorithm in ['RS256', 'ES256']:
        print("\n⚠️  Your Supabase project uses asymmetric key signing!")
        print("This is the newer, more secure method.")
        print("\nYou need to update the code to:")
        print("1. Fetch public keys from JWKS endpoint")
        print("2. Use RS256/ES256 for verification")
        print("\nSee: https://supabase.com/docs/guides/auth/jwts")


if __name__ == '__main__':
    test_jwt_secret()
