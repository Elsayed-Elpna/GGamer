from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from .managers import UserManager


# ============================
# User Model
# ============================

class User(AbstractBaseUser, PermissionsMixin):

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        SELLER = "SELLER", "Seller"
        BUYER = "BUYER", "Buyer"
        SUPPORT = "SUPPORT", "Support"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.BUYER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    is_banned = models.BooleanField(default=False)
    ban_reason = models.TextField(blank=True, null=True)

    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


# ============================
# Public Profile
# ============================

class PublicProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="public_profile")

    username = models.CharField(max_length=50, unique=True)
    bio = models.TextField(blank=True)

    rating = models.FloatField(default=0)
    completed_orders = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username


# ============================
# Private Profile
# ============================

class PrivateProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="private_profile")

    phone_number = models.CharField(max_length=20)
    national_id = models.CharField(max_length=20)

    def __str__(self):
        return f"Private profile of {self.user.email}"