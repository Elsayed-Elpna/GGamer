from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """
    Permission check for admin users.
    Ensures user is authenticated, active, not banned, and has ADMIN role.
    """
    message = "Only administrators can access this resource."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.is_active and
            not request.user.is_banned and
            request.user.role == "ADMIN"
        )


class IsSupport(BasePermission):
    """
    Permission check for support staff.
    Ensures user is authenticated, active, not banned, and has SUPPORT role.
    """
    message = "Only support staff can access this resource."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.is_active and
            not request.user.is_banned and
            request.user.role == "SUPPORT"
        )

