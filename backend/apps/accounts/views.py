from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from .models import User, PublicProfile, PrivateProfile
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    PublicProfileSerializer,
    PrivateProfileSerializer
)
from .permissions import IsAdmin
from common.permissions import IsNotBanned
from common.validators import (
    FileSizeValidator,
    FileTypeValidator,
    ImageDimensionValidator,
    validate_safe_filename
)

import logging

logger = logging.getLogger('security')


# ============================
# Rate Limiting Classes
# ============================

class AuthRateThrottle(AnonRateThrottle):
    """
    Rate limiting for authentication endpoints.
    5 requests per minute to prevent brute force attacks.
    """
    rate = "5/min"


class FileUploadRateThrottle(UserRateThrottle):
    """
    Rate limiting for file upload endpoints.
    10 uploads per minute to prevent abuse.
    """
    rate = "10/min"


class ProfileUpdateRateThrottle(UserRateThrottle):
    """
    Rate limiting for profile update endpoints.
    20 updates per minute.
    """
    rate = "20/min"


# ============================
# Register
# ============================

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def register_view(request):
    """
    Register a new user account.
    Creates user and public profile automatically.
    """
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        logger.info(f"New user registered: {user.email}")
        return Response(
            {"message": "Account created successfully. Please verify your email."},
            status=status.HTTP_201_CREATED
        )

    logger.warning(f"Registration failed: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================
# My Profile
# ============================

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsNotBanned])
def me_view(request):
    """
    Get current user's profile information.
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


# ============================
# Update Avatar
# ============================

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsNotBanned])
@throttle_classes([FileUploadRateThrottle])
def upload_avatar(request):
    """
    Upload or update user avatar.
    Validates file type, size, and dimensions.
    """
    avatar = request.FILES.get("avatar")

    if not avatar:
        return Response(
            {"error": "Avatar file is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate file
    validators = [
        FileSizeValidator(max_size_mb=5),
        FileTypeValidator(allowed_types=['image/jpeg', 'image/png', 'image/gif', 'image/webp']),
        ImageDimensionValidator(max_width=2048, max_height=2048, min_width=100, min_height=100),
    ]

    for validator in validators:
        try:
            validator(avatar)
        except ValidationError as e:
            logger.warning(f"Avatar upload validation failed for user {request.user.email}: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Validate filename
    try:
        validate_safe_filename(avatar)
    except ValidationError as e:
        logger.warning(f"Unsafe filename detected for user {request.user.email}: {avatar.name}")
        return Response(
            {"error": "Invalid filename"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Save avatar
    request.user.avatar = avatar
    request.user.save()

    logger.info(f"Avatar updated for user {request.user.email}")
    return Response(
        {"message": "Avatar updated successfully"},
        status=status.HTTP_200_OK
    )


# ============================
# Update Public Profile
# ============================

@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, IsNotBanned])
@throttle_classes([ProfileUpdateRateThrottle])
def update_public_profile(request):
    """
    Get or update user's public profile.
    """
    profile, created = PublicProfile.objects.get_or_create(user=request.user)

    if request.method == "GET":
        serializer = PublicProfileSerializer(profile)
        return Response(serializer.data)

    # PATCH - Update profile
    serializer = PublicProfileSerializer(profile, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        logger.info(f"Public profile updated for user {request.user.email}")
        return Response(serializer.data)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================
# Private Profile
# ============================

@api_view(["GET", "POST", "PATCH"])
@permission_classes([IsAuthenticated, IsNotBanned])
@throttle_classes([ProfileUpdateRateThrottle])
def private_profile_view(request):
    """
    Get, create, or update user's private profile (KYC data).
    """
    try:
        profile = PrivateProfile.objects.get(user=request.user)
        exists = True
    except PrivateProfile.DoesNotExist:
        profile = None
        exists = False

    if request.method == "GET":
        if not exists:
            return Response(
                {"message": "Private profile not created yet"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = PrivateProfileSerializer(profile)
        return Response(serializer.data)

    # POST or PATCH - Create or update
    if request.method == "POST" and exists:
        return Response(
            {"error": "Private profile already exists. Use PATCH to update."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if request.method == "POST":
        serializer = PrivateProfileSerializer(data=request.data)
    else:  # PATCH
        if not exists:
            return Response(
                {"error": "Private profile does not exist. Use POST to create."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = PrivateProfileSerializer(profile, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save(user=request.user)
        logger.info(f"Private profile {'created' if request.method == 'POST' else 'updated'} for user {request.user.email}")
        return Response(serializer.data, status=status.HTTP_201_CREATED if request.method == "POST" else status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================
# Ban User (ADMIN ONLY)
# ============================

@api_view(["POST"])
@permission_classes([IsAdmin, IsNotBanned])
def ban_user(request, user_id):
    """
    Ban a user account (Admin only).
    Prevents banning superusers and self-banning.
    """
    user = get_object_or_404(User, id=user_id)

    # Prevent banning superusers
    if user.is_superuser:
        logger.warning(f"Admin {request.user.email} attempted to ban superuser {user.email}")
        return Response(
            {"error": "Cannot ban superuser accounts"},
            status=status.HTTP_403_FORBIDDEN
        )

    # Prevent self-banning
    if user.id == request.user.id:
        logger.warning(f"Admin {request.user.email} attempted to ban themselves")
        return Response(
            {"error": "Cannot ban yourself"},
            status=status.HTTP_403_FORBIDDEN
        )

    # Check if already banned
    if user.is_banned:
        return Response(
            {"message": "User is already banned"},
            status=status.HTTP_200_OK
        )

    # Ban the user
    ban_reason = request.data.get("reason", "No reason provided")
    user.ban(reason=ban_reason)

    logger.warning(
        f"User {user.email} (ID: {user.id}) banned by admin {request.user.email}. "
        f"Reason: {ban_reason}"
    )

    return Response(
        {"message": "User banned successfully"},
        status=status.HTTP_200_OK
    )


# ============================
# Unban User (ADMIN ONLY)
# ============================

@api_view(["POST"])
@permission_classes([IsAdmin, IsNotBanned])
def unban_user(request, user_id):
    """
    Unban a user account (Admin only).
    """
    user = get_object_or_404(User, id=user_id)

    if not user.is_banned:
        return Response(
            {"message": "User is not banned"},
            status=status.HTTP_200_OK
        )

    user.unban()

    logger.info(f"User {user.email} (ID: {user.id}) unbanned by admin {request.user.email}")

    return Response(
        {"message": "User unbanned successfully"},
        status=status.HTTP_200_OK
    )