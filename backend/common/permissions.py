"""
Reusable permission classes for the marketplace application.
Includes permissions for banned users, email verification, and self-or-admin access.
"""
from rest_framework.permissions import BasePermission


class IsNotBanned(BasePermission):
    """
    Permission check to ensure user is not banned.
    This should be used on all authenticated endpoints.
    """
    message = "Your account has been banned. Please contact support."
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return True  # Let authentication handle this
        
        return not request.user.is_banned


class IsEmailVerified(BasePermission):
    """
    Permission check to ensure user has verified their email.
    Use this for sensitive operations like payments or selling.
    """
    message = "Please verify your email address to access this feature."
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return True  # Let authentication handle this
        
        # Check if user has email_verified field (will be added in migration)
        return getattr(request.user, 'email_verified', True)


class IsSelfOrAdmin(BasePermission):
    """
    Permission check to ensure user can only access/modify their own resources,
    unless they are an admin.
    """
    message = "You can only access your own profile."
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin can access anything
        if request.user.role == 'ADMIN':
            return True
        
        # Check if object has a 'user' attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # If object IS the user
        return obj == request.user


class IsAdminOrSupport(BasePermission):
    """
    Permission check for admin or support staff.
    """
    message = "Only admin or support staff can access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in ['ADMIN', 'SUPPORT']
        )


class IsActiveUser(BasePermission):
    """
    Permission check to ensure user account is active.
    """
    message = "Your account is inactive. Please contact support."
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return True  # Let authentication handle this
        
        return request.user.is_active
