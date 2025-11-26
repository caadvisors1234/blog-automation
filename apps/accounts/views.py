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


def login_view(request):
    """
    Login view.
    
    Note: Actual authentication is handled by Supabase on the frontend.
    This view handles the redirect after Supabase authentication.
    """
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    # For demo/development, allow simple login
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Try to find user by email first
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            username = email  # Fall back to using email as username
        
        # Try to authenticate
        from django.contrib.auth import authenticate
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            auth_login(request, user)
            messages.success(request, 'ログインしました')
            next_url = request.GET.get('next', 'core:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'メールアドレスまたはパスワードが正しくありません')
    
    return render(request, 'accounts/login.html')


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
