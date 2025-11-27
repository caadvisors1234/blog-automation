# -*- coding: utf-8 -*-
"""
Tests for Supabase authentication functionality
"""

import json
import jwt
from datetime import datetime, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse
from apps.accounts.models import LoginAttempt
from apps.accounts.utils import verify_supabase_token

User = get_user_model()


class SupabaseAuthenticationTest(TestCase):
    """Test suite for Supabase authentication"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        self.login_url = reverse('accounts:supabase_login')

        # Create test user
        self.test_user = User.objects.create(
            username='testuser',
            email='test@example.com',
            supabase_user_id='test-supabase-id-123'
        )

    def create_test_token(self, supabase_user_id='test-supabase-id-123',
                         email='test@example.com', expired=False):
        """
        Create a test JWT token for testing

        Args:
            supabase_user_id: Supabase user ID
            email: User email
            expired: If True, create an expired token

        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)

        payload = {
            'sub': supabase_user_id,
            'email': email,
            'aud': 'authenticated',
            'iat': int(now.timestamp()),
            'exp': int(exp.timestamp())
        }

        token = jwt.encode(
            payload,
            settings.SUPABASE_JWT_SECRET,
            algorithm='HS256'
        )

        return token

    def test_jwt_verification_with_valid_token(self):
        """Test JWT verification with a valid token"""
        token = self.create_test_token()
        payload = verify_supabase_token(token)

        self.assertIsNotNone(payload)
        self.assertEqual(payload['sub'], 'test-supabase-id-123')
        self.assertEqual(payload['email'], 'test@example.com')

    def test_jwt_verification_with_expired_token(self):
        """Test JWT verification with an expired token"""
        token = self.create_test_token(expired=True)
        payload = verify_supabase_token(token)

        self.assertIsNone(payload)

    def test_jwt_verification_with_invalid_token(self):
        """Test JWT verification with an invalid token"""
        invalid_token = 'invalid.jwt.token'
        payload = verify_supabase_token(invalid_token)

        self.assertIsNone(payload)

    def test_successful_login_existing_user(self):
        """Test successful login with existing user"""
        token = self.create_test_token()

        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'access_token': token,
                'remember': False
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['username'], 'testuser')

        # Check login attempt was recorded
        login_attempt = LoginAttempt.objects.filter(
            email='test@example.com',
            success=True
        ).first()
        self.assertIsNotNone(login_attempt)

    def test_successful_login_new_user(self):
        """Test successful login with new user (auto-creation)"""
        new_user_id = 'new-user-id-456'
        new_email = 'newuser@example.com'
        token = self.create_test_token(
            supabase_user_id=new_user_id,
            email=new_email
        )

        # Verify user doesn't exist yet
        self.assertFalse(User.objects.filter(email=new_email).exists())

        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'access_token': token,
                'remember': True
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

        # Verify user was created
        new_user = User.objects.get(email=new_email)
        self.assertEqual(new_user.supabase_user_id, new_user_id)
        self.assertEqual(new_user.username, 'newuser')

        # Check login attempt was recorded
        login_attempt = LoginAttempt.objects.filter(
            email=new_email,
            success=True
        ).first()
        self.assertIsNotNone(login_attempt)

    def test_failed_login_invalid_token(self):
        """Test failed login with invalid token"""
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'access_token': 'invalid.token.here',
                'remember': False
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn('error', data)

        # Check failed login attempt was recorded
        login_attempt = LoginAttempt.objects.filter(
            success=False
        ).first()
        self.assertIsNotNone(login_attempt)

    def test_failed_login_expired_token(self):
        """Test failed login with expired token"""
        token = self.create_test_token(expired=True)

        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'access_token': token,
                'remember': False
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_failed_login_missing_token(self):
        """Test failed login with missing access token"""
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'remember': False
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_failed_login_invalid_json(self):
        """Test failed login with invalid JSON"""
        response = self.client.post(
            self.login_url,
            data='invalid json{{{',
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

        # Check failed login attempt was recorded
        login_attempt = LoginAttempt.objects.filter(
            success=False,
            failure_reason='Invalid JSON format'
        ).first()
        self.assertIsNotNone(login_attempt)

    def test_session_expiry_remember_false(self):
        """Test session expiry when remember=False"""
        token = self.create_test_token()

        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'access_token': token,
                'remember': False
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        # Session should expire on browser close
        self.assertEqual(self.client.session.get_expiry_age(), 0)

    def test_session_expiry_remember_true(self):
        """Test session expiry when remember=True"""
        token = self.create_test_token()

        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'access_token': token,
                'remember': True
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        # Session should last 14 days
        self.assertEqual(self.client.session.get_expiry_age(), 1209600)

    def test_login_attempt_tracking(self):
        """Test that login attempts are properly tracked"""
        # Initial count
        initial_count = LoginAttempt.objects.count()

        # Make a successful login
        token = self.create_test_token()
        self.client.post(
            self.login_url,
            data=json.dumps({
                'access_token': token,
                'remember': False
            }),
            content_type='application/json'
        )

        # Make a failed login
        self.client.post(
            self.login_url,
            data=json.dumps({
                'access_token': 'invalid',
                'remember': False
            }),
            content_type='application/json'
        )

        # Check that 2 new attempts were recorded
        self.assertEqual(LoginAttempt.objects.count(), initial_count + 2)

        # Check successful attempt
        success_attempt = LoginAttempt.objects.filter(success=True).first()
        self.assertEqual(success_attempt.user, self.test_user)
        self.assertEqual(success_attempt.email, 'test@example.com')

        # Check failed attempt
        failed_attempt = LoginAttempt.objects.filter(success=False).first()
        self.assertFalse(failed_attempt.success)
        self.assertIsNotNone(failed_attempt.failure_reason)

    def test_rate_limiting(self):
        """Test rate limiting on login endpoint"""
        token = self.create_test_token()

        # Make multiple rapid requests (more than rate limit)
        responses = []
        for _ in range(6):  # Rate limit is 5/minute
            response = self.client.post(
                self.login_url,
                data=json.dumps({
                    'access_token': token,
                    'remember': False
                }),
                content_type='application/json'
            )
            responses.append(response)

        # At least one request should be rate limited (429)
        status_codes = [r.status_code for r in responses]
        self.assertIn(429, status_codes)
