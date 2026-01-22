from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import UserRateThrottle

from django.shortcuts import get_object_or_404

from .models import User, PublicProfile, PrivateProfile
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    PublicProfileSerializer,
    PrivateProfileSerializer
)
from .permissions import IsAdmin

# ============================
# Rate Limit
# ============================

class AuthRateThrottle(UserRateThrottle):
    rate = "5/min"


# ============================
# Register
# ============================
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def register_view(request):

    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Account created successfully"}, status=201)

    return Response(serializer.errors, status=400)

# ============================
# My Profile
# ============================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):

    serializer = UserSerializer(request.user)
    return Response(serializer.data)

# ============================
# Update Avatar
# ============================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_avatar(request):

    avatar = request.FILES.get("avatar")

    if not avatar:
        return Response({"error": "Avatar required"}, status=400)

    request.user.avatar = avatar
    request.user.save()

    return Response({"message": "Avatar updated"})

# ============================
# Private Profile
# ============================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_private_profile(request):

    profile, created = PrivateProfile.objects.get_or_create(user=request.user)

    serializer = PrivateProfileSerializer(profile, data=request.data)

    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data)

    return Response(serializer.errors, status=400)


# ============================
# Ban User (ADMIN)
# ============================


@api_view(["POST"])
@permission_classes([IsAdmin])
def ban_user(request, user_id):

    user = get_object_or_404(User, id=user_id)

    user.is_banned = True
    user.ban_reason = request.data.get("reason", "")
    user.save()

    return Response({"message": "User banned successfully"})