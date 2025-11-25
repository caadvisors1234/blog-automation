# -*- coding: utf-8 -*-
"""
Serializers for user and authentication
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.blog.models import SALONBoardAccount

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
            'hpb_salon_url',
            'hpb_salon_id',
            'date_joined',
            'has_salon_board_account',
        ]
        read_only_fields = [
            'id',
            'supabase_user_id',
            'hpb_salon_id',  # Auto-extracted from URL
            'date_joined',
        ]

    def get_has_salon_board_account(self, obj):
        """Check if user has SALON BOARD account"""
        try:
            return hasattr(obj, 'salon_board_account') and obj.salon_board_account.is_active
        except SALONBoardAccount.DoesNotExist:
            return False


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile
    """

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'hpb_salon_url',
        ]

    def update(self, instance, validated_data):
        """
        Update user and auto-extract salon ID from URL

        Args:
            instance: User instance
            validated_data: Validated data

        Returns:
            Updated User instance
        """
        # Salon ID will be auto-extracted in model's save method
        return super().update(instance, validated_data)


class SALONBoardAccountSerializer(serializers.ModelSerializer):
    """
    SALON BOARD account serializer
    """
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = SALONBoardAccount
        fields = [
            'id',
            'login_id',
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

        if not password:
            raise serializers.ValidationError({'password': 'Password is required'})

        # Create account
        account = SALONBoardAccount(
            user=user,
            login_id=validated_data['login_id'],
            is_active=validated_data.get('is_active', True)
        )

        # Encrypt and set password
        account.set_password(password)
        account.save()

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

        # Update login_id and is_active
        instance.login_id = validated_data.get('login_id', instance.login_id)
        instance.is_active = validated_data.get('is_active', instance.is_active)

        # Update password if provided
        if password:
            instance.set_password(password)

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
