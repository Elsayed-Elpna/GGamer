from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from .managers import UserManager
from common.validators import (
    phone_regex,
    validate_egyptian_national_id,
    FileSizeValidator,
    FileTypeValidator,
    username_regex,
    validate_username_not_email
)


# ============================
# User Model
# ============================

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model with email-based authentication.
    Supports role-based access control and ban system.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        SELLER = "SELLER", "Seller"
        BUYER = "BUYER", "Buyer"
        SUPPORT = "SUPPORT", "Support"

    # Core fields
    email = models.EmailField(unique=True, db_index=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.BUYER, db_index=True)

    # Account status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)

    # Ban system
    is_banned = models.BooleanField(default=False, db_index=True)
    ban_reason = models.TextField(blank=True, null=True)
    banned_at = models.DateTimeField(blank=True, null=True)

    # Avatar with validation
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
        validators=[
            FileSizeValidator(max_size_mb=5),
            FileTypeValidator(allowed_types=['image/jpeg', 'image/png', 'image/gif', 'image/webp'])
        ],
        help_text="Max size: 5MB. Allowed formats: JPEG, PNG, GIF, WebP"
    )

    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_banned']),
        ]

    def __str__(self):
        return self.email

    def ban(self, reason=""):
        """Ban this user with a reason."""
        self.is_banned = True
        self.ban_reason = reason
        self.banned_at = timezone.now()
        self.save()

    def unban(self):
        """Unban this user."""
        self.is_banned = False
        self.ban_reason = None
        self.banned_at = None
        self.save()


# ============================
# Public Profile
# ============================

class PublicProfile(models.Model):
    """
    Public-facing user profile visible to all users.
    Contains non-sensitive information like username, bio, and ratings.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="public_profile")

    username = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        validators=[username_regex, validate_username_not_email],
        help_text="3-50 characters. Letters, numbers, underscores, and hyphens only."
    )
    bio = models.TextField(blank=True, max_length=500)

    # Reputation metrics
    rating = models.FloatField(default=0.0)
    completed_orders = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['username']),
        ]

    def __str__(self):
        return self.username


# ============================
# Private Profile
# ============================

class PrivateProfile(models.Model):
    """
    Private user profile containing sensitive PII.
    Only accessible by the user themselves and admins.
    Required for KYC verification.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="private_profile")

    # PII fields with validation
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[phone_regex],
        db_index=True,
        help_text="Egyptian mobile number (e.g., 01012345678)"
    )
    national_id = models.CharField(
        max_length=14,
        unique=True,
        validators=[validate_egyptian_national_id],
        db_index=True,
        help_text="14-digit Egyptian National ID"
    )

    # Verification status
    phone_verified = models.BooleanField(default=False)
    national_id_verified = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['national_id']),
        ]

    def __str__(self):
        return f"Private profile of {self.user.email}"