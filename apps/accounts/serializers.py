# -*- coding: utf-8 -*-
"""
Serializers for user and authentication
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.blog.models import SALONBoardAccount
from cryptography.fernet import Fernet
from django.conf import settings

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    User model serializer
    """
    has_salon_board_account = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'supabase_user_id',
            'date_joined',
            'has_salon_board_account',
        ]
        read_only_fields = [
            'id',
            'supabase_user_id',
            'date_joined',
        ]

    def get_has_salon_board_account(self, obj):
        """Check if user has SALON BOARD account"""
        try:
            return hasattr(obj, 'salon_board_account') and obj.salon_board_account.is_active
        except SALONBoardAccount.DoesNotExist:
            return False


class SALONBoardAccountSerializer(serializers.ModelSerializer):
    """
    SALON BOARD account serializer
    """
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = SALONBoardAccount
        fields = [
            'id',
            'email',
            'password',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        """
        Create SALON BOARD account with encrypted password

        Args:
            validated_data: Validated data from request

        Returns:
            Created SALONBoardAccount instance
        """
        password = validated_data.pop('password', None)
        user = self.context['request'].user

        # Encrypt password
        fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        encrypted_password = fernet.encrypt(password.encode()).decode()

        # Create account
        account = SALONBoardAccount.objects.create(
            user=user,
            email=validated_data['email'],
            encrypted_password=encrypted_password,
            is_active=validated_data.get('is_active', True)
        )

        return account

    def update(self, instance, validated_data):
        """
        Update SALON BOARD account

        Args:
            instance: Existing SALONBoardAccount instance
            validated_data: Validated data from request

        Returns:
            Updated SALONBoardAccount instance
        """
        password = validated_data.pop('password', None)

        # Update email and is_active
        instance.email = validated_data.get('email', instance.email)
        instance.is_active = validated_data.get('is_active', instance.is_active)

        # Update password if provided
        if password:
            fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            instance.encrypted_password = fernet.encrypt(password.encode()).decode()

        instance.save()
        return instance

    def to_representation(self, instance):
        """
        Customize representation to hide encrypted password

        Args:
            instance: SALONBoardAccount instance

        Returns:
            Serialized data
        """
        data = super().to_representation(instance)
        # Remove encrypted_password from response
        data.pop('encrypted_password', None)
        return data
