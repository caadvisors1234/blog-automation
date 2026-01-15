# -*- coding: utf-8 -*-
"""
User and account management views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from rest_framework import serializers as drf_serializers
from .serializers import UserSerializer, UserUpdateSerializer, SALONBoardAccountSerializer
from apps.blog.models import SALONBoardAccount, BlogPostTemplate

User = get_user_model()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    User management viewset

    Provides endpoints for:
    - GET /api/accounts/users/me/ - Get current user profile
    - PATCH /api/accounts/users/me/ - Update current user profile
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Limit user access to the authenticated user only.
        """
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        """
        Get or update current user profile

        Args:
            request: HTTP request

        Returns:
            User profile data
        """
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)

        elif request.method == 'PATCH':
            serializer = UserUpdateSerializer(
                request.user,
                data=request.data,
                partial=True,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Return full user data
            return Response(UserSerializer(request.user).data)


class SALONBoardAccountViewSet(viewsets.ModelViewSet):
    """
    SALON BOARD account management viewset

    Provides endpoints for:
    - GET /api/accounts/salon-board-accounts/ - Get user's SALON BOARD account
    - POST /api/accounts/salon-board-accounts/ - Create new SALON BOARD account
    - GET /api/accounts/salon-board-accounts/{id}/ - Get specific account
    - PATCH /api/accounts/salon-board-accounts/{id}/ - Update account
    - DELETE /api/accounts/salon-board-accounts/{id}/ - Delete account
    """
    serializer_class = SALONBoardAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Get SALON BOARD accounts for current user

        Returns:
            QuerySet of user's SALON BOARD accounts
        """
        return SALONBoardAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        Create SALON BOARD account for current user

        Args:
            serializer: Validated serializer instance
        """
        # Check if user already has an account
        if SALONBoardAccount.objects.filter(user=self.request.user).exists():
            raise drf_serializers.ValidationError({
                'detail': 'User already has a SALON BOARD account'
            })

        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='current')
    def current(self, request):
        """
        Get current user's SALON BOARD account

        Args:
            request: HTTP request

        Returns:
            SALON BOARD account data or 404
        """
        try:
            account = request.user.salon_board_account
            serializer = self.get_serializer(account)
            return Response(serializer.data)
        except SALONBoardAccount.DoesNotExist:
            return Response(
                {'detail': 'No SALON BOARD account found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ========================================
# Template Views (Frontend)
# ========================================

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit
from .utils import verify_supabase_token
from .models import LoginAttempt
import json
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get the client IP address from the request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def login_view(request):
    """
    Login view.

    Displays the login form. Authentication is handled by Supabase on the frontend.
    """
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    from django.conf import settings

    context = {
        'SUPABASE_URL': settings.SUPABASE_URL,
        'SUPABASE_KEY': settings.SUPABASE_KEY,
    }

    return render(request, 'accounts/login.html', context)


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_POST
def supabase_login_view(request):
    """
    Handle Supabase authentication and create Django session.

    This endpoint receives a Supabase JWT access token from the frontend,
    verifies it, and creates a Django session for the authenticated user.

    Args:
        request: HTTP request with JSON body containing:
            - access_token: Supabase JWT access token
            - remember: Boolean for session persistence

    Returns:
        JSON response with redirect URL or error message
    """
    # Get client information
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    try:
        # Parse request body
        data = json.loads(request.body)
        access_token = data.get('access_token')
        remember = data.get('remember', False)

        logger.info(
            "Supabase login attempt from IP %s - Token length: %s",
            ip_address,
            len(access_token) if access_token else 0,
        )

        if not access_token:
            logger.warning('Supabase login failed: No access token provided')
            return JsonResponse(
                {'error': 'アクセストークンが必要です'},
                status=400
            )

        # Verify Supabase JWT token
        payload = verify_supabase_token(access_token)

        if not payload:
            logger.error("JWT token verification failed")
            # Record failed login attempt
            email = payload.get('email', 'unknown') if payload else 'unknown'
            LoginAttempt.objects.create(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason='JWT token verification failed'
            )
            return JsonResponse(
                {'error': 'トークンの検証に失敗しました'},
                status=401
            )

        logger.info("JWT token verified successfully")

        # Extract user information from token
        supabase_user_id = payload.get('sub')
        email = payload.get('email')

        if not supabase_user_id:
            return JsonResponse(
                {'error': 'トークンにユーザー情報が含まれていません'},
                status=400
            )

        # Get or create user
        try:
            user = User.objects.get(supabase_user_id=supabase_user_id)
            logger.info(f'Existing user logged in: {user.username} (supabase_id: {supabase_user_id})')
        except User.DoesNotExist:
            # Create new user from Supabase data
            username = email.split('@')[0] if email else f'user_{supabase_user_id[:8]}'

            # Ensure username is unique
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f'{base_username}{counter}'
                counter += 1

            user = User.objects.create(
                username=username,
                email=email or '',
                supabase_user_id=supabase_user_id
            )
            logger.info(f'New user created: {user.username} (supabase_id: {supabase_user_id})')

        # Log the user in (create Django session)
        auth_login(request, user, backend='apps.accounts.backends.SupabaseAuthBackend')

        # Configure session expiry based on remember option
        if not remember:
            # Session expires when browser closes
            request.session.set_expiry(0)
        else:
            # Session lasts for 2 weeks
            request.session.set_expiry(1209600)  # 14 days in seconds

        logger.info(f'Django session created for user: {user.username}')

        # Record successful login attempt
        LoginAttempt.objects.create(
            user=user,
            email=email or '',
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )

        return JsonResponse({
            'success': True,
            'redirect_url': '/',  # Dashboard is at root URL
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })

    except json.JSONDecodeError:
        # Record failed login attempt
        LoginAttempt.objects.create(
            email='unknown',
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason='Invalid JSON format'
        )
        return JsonResponse(
            {'error': 'リクエストの形式が正しくありません'},
            status=400
        )
    except Exception as e:
        logger.error(f'Login error: {str(e)}', exc_info=True)
        # Record failed login attempt
        try:
            email_addr = payload.get('email', 'unknown') if 'payload' in locals() else 'unknown'
        except:
            email_addr = 'unknown'
        LoginAttempt.objects.create(
            email=email_addr,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason=f'Exception: {str(e)[:200]}'
        )
        return JsonResponse(
            {'error': 'ログイン処理中にエラーが発生しました'},
            status=500
        )


def logout_view(request):
    """
    Logout view.
    """
    auth_logout(request)
    messages.success(request, 'ログアウトしました')
    return redirect('accounts:login')


@login_required
def settings_view(request):
    """
    User settings view.

    Allows users to:
    - Update HPB salon URL
    - Manage SALON BOARD credentials
    - Manage blog post templates
    """
    user = request.user
    salon_account = None

    try:
        salon_account = user.salon_board_account
    except SALONBoardAccount.DoesNotExist:
        pass

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            # Update HPB salon URL
            hpb_salon_url = request.POST.get('hpb_salon_url', '').strip()
            user.hpb_salon_url = hpb_salon_url
            user.save()
            messages.success(request, 'プロフィールを更新しました')

        elif action == 'update_salon_board':
            # Update or create SALON BOARD account
            login_id = request.POST.get('login_id', '').strip()
            password = request.POST.get('password', '').strip()

            if login_id:
                if salon_account:
                    salon_account.login_id = login_id
                    if password:
                        salon_account.set_password(password)
                    salon_account.save()
                else:
                    salon_account = SALONBoardAccount.objects.create(
                        user=user,
                        login_id=login_id,
                    )
                    if password:
                        salon_account.set_password(password)
                        salon_account.save()

                messages.success(request, 'SALON BOARDアカウントを更新しました')

        elif action == 'delete_salon_board':
            if salon_account:
                salon_account.delete()
                salon_account = None
                messages.success(request, 'SALON BOARDアカウントを削除しました')

        elif action == 'create_template':
            # Create blog post template
            template_name = request.POST.get('template_name', '').strip()
            template_content = request.POST.get('template_content', '').strip()

            # Validation
            if not template_name:
                messages.error(request, 'テンプレート名を入力してください')
            elif not template_content:
                messages.error(request, 'テンプレート内容を入力してください')
            elif len(template_content) > 500:
                messages.error(request, 'テンプレート内容は500文字以内にしてください')
            elif BlogPostTemplate.objects.filter(user=user, name=template_name).exists():
                messages.error(request, 'この名前のテンプレートは既に存在します')
            else:
                BlogPostTemplate.objects.create(
                    user=user,
                    name=template_name,
                    content=template_content
                )
                messages.success(request, 'テンプレートを作成しました')

        elif action == 'delete_template':
            # Delete blog post template
            template_id = request.POST.get('template_id')
            if template_id:
                try:
                    template = BlogPostTemplate.objects.get(id=template_id, user=user)
                    template.delete()
                    messages.success(request, 'テンプレートを削除しました')
                except BlogPostTemplate.DoesNotExist:
                    messages.error(request, 'テンプレートが見つかりませんでした')

        return redirect('accounts:settings')

    # Get user's blog post templates
    templates = BlogPostTemplate.objects.filter(user=user).order_by('-created_at')

    context = {
        'user': user,
        'salon_account': salon_account,
        'templates': templates,
    }

    return render(request, 'accounts/settings.html', context)
