from rest_framework import serializers
from .models import User, PublicProfile, PrivateProfile
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
import logging

logger = logging.getLogger('accounts')


# ============================
# Register Serializer
# ============================

class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Includes password confirmation and automatic public profile creation.
    """

    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ("email", "password", "password_confirm")

    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                "password_confirm": "Passwords do not match"
            })
        return attrs

    def create(self, validated_data):
        """
        Create user with secure password hashing and public profile.
        Handles username uniqueness conflicts gracefully.
        """
        # Remove password_confirm before creating user
        validated_data.pop('password_confirm')

        # Create user
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )

        # Generate unique username from email
        base_username = user.email.split("@")[0]
        username = base_username
        counter = 1

        # Keep trying until we find a unique username
        while True:
            try:
                PublicProfile.objects.create(user=user, username=username)
                logger.info(f"Created public profile for user {user.email} with username {username}")
                break
            except IntegrityError:
                # Username already exists, try with counter
                username = f"{base_username}{counter}"
                counter += 1
                if counter > 1000:  # Safety limit
                    logger.error(f"Failed to generate unique username for {user.email}")
                    user.delete()  # Rollback user creation
                    raise serializers.ValidationError(
                        "Unable to generate unique username. Please contact support."
                    )

        return user


# ============================
# Public Profile Serializer
# ============================

class PublicProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for public profile.
    Only exposes safe, non-sensitive fields.
    """

    class Meta:
        model = PublicProfile
        fields = (
            "username",
            "bio",
            "rating",
            "completed_orders",
            "created_at"
        )
        read_only_fields = ("rating", "completed_orders", "created_at")


# ============================
# Private Profile Serializer
# ============================

class PrivateProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for private profile containing PII.
    Masks sensitive data in responses.
    """

    # Display masked versions in responses
    phone_number_masked = serializers.SerializerMethodField()
    national_id_masked = serializers.SerializerMethodField()

    class Meta:
        model = PrivateProfile
        fields = (
            "phone_number",
            "national_id",
            "phone_number_masked",
            "national_id_masked",
            "phone_verified",
            "national_id_verified",
            "created_at",
            "updated_at"
        )
        read_only_fields = (
            "phone_verified",
            "national_id_verified",
            "phone_number_masked",
            "national_id_masked",
            "created_at",
            "updated_at"
        )
        extra_kwargs = {
            'phone_number': {'write_only': True},
            'national_id': {'write_only': True},
        }

    def get_phone_number_masked(self, obj):
        """Mask phone number for display: 0101234**** """
        if obj.phone_number:
            return obj.phone_number[:7] + "****"
        return None

    def get_national_id_masked(self, obj):
        """Mask national ID for display: 12345********* """
        if obj.national_id:
            return obj.national_id[:5] + "*********"
        return None

    def validate_phone_number(self, value):
        """Ensure phone number is unique across all users."""
        if self.instance:
            # Updating existing profile
            if PrivateProfile.objects.exclude(pk=self.instance.pk).filter(phone_number=value).exists():
                raise serializers.ValidationError("This phone number is already registered.")
        else:
            # Creating new profile
            if PrivateProfile.objects.filter(phone_number=value).exists():
                raise serializers.ValidationError("This phone number is already registered.")
        return value

    def validate_national_id(self, value):
        """Ensure national ID is unique across all users."""
        if self.instance:
            # Updating existing profile
            if PrivateProfile.objects.exclude(pk=self.instance.pk).filter(national_id=value).exists():
                raise serializers.ValidationError("This national ID is already registered.")
        else:
            # Creating new profile
            if PrivateProfile.objects.filter(national_id=value).exists():
                raise serializers.ValidationError("This national ID is already registered.")
        return value


# ============================
# User Serializer (Safe)
# ============================

class UserSerializer(serializers.ModelSerializer):
    """
    Safe user serializer that only exposes non-sensitive fields.
    Includes nested public profile.
    """

    public_profile = PublicProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "role",
            "avatar",
            "email_verified",
            "date_joined",
            "public_profile"
        )
        read_only_fields = (
            "id",
            "email",
            "role",
            "email_verified",
            "date_joined"
        )


# ============================
# Admin User Serializer
# ============================

class AdminUserSerializer(serializers.ModelSerializer):
    """
    Admin-only serializer with additional fields for user management.
    """

    public_profile = PublicProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "role",
            "is_active",
            "is_banned",
            "ban_reason",
            "banned_at",
            "email_verified",
            "date_joined",
            "updated_at",
            "public_profile"
        )
        read_only_fields = ("id", "date_joined", "updated_at")

