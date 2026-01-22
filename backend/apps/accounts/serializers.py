from rest_framework import serializers
from .models import User, PublicProfile, PrivateProfile
from django.contrib.auth.password_validation import validate_password


# ============================
# Register Serializer
# ============================

class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("email", "password")

    def create(self, validated_data):

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )

        PublicProfile.objects.create(user=user, username=user.email.split("@")[0])

        return user


# ============================
# Public Profile Serializer
# ============================

class PublicProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = PublicProfile
        fields = "__all__"
        read_only_fields = ("user", "rating", "completed_orders")


# ============================
# Private Profile Serializer
# ============================

class PrivateProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = PrivateProfile
        fields = "__all__"
        read_only_fields = ("user",)


# ============================
# User Serializer (Safe)
# ============================

class UserSerializer(serializers.ModelSerializer):

    public_profile = PublicProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "role", "avatar", "public_profile")
