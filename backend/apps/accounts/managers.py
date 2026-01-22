from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """
    Custom manager for email-based authentication
    """

    def create_user(self, email, password=None, **extra_fields):

        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields
        )

        user.set_password(password)  # secure hashing
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "ADMIN")

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must be staff")

        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must be superuser")

        return self.create_user(email, password, **extra_fields)
