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
from .serializers import UserSerializer, SALONBoardAccountSerializer
from apps.blog.models import SALONBoardAccount

User = get_user_model()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    User management viewset

    Provides endpoints for:
    - GET /api/users/me/ - Get current user profile
    - PATCH /api/users/me/ - Update current user profile
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
            serializer = self.get_serializer(
                request.user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)


class SALONBoardAccountViewSet(viewsets.ModelViewSet):
    """
    SALON BOARD account management viewset

    Provides endpoints for:
    - GET /api/salon-board-accounts/ - List user's SALON BOARD accounts
    - POST /api/salon-board-accounts/ - Create new SALON BOARD account
    - GET /api/salon-board-accounts/{id}/ - Get specific account
    - PATCH /api/salon-board-accounts/{id}/ - Update account
    - DELETE /api/salon-board-accounts/{id}/ - Delete account
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
