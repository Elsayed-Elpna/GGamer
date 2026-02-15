"""
Custom permissions for verification app.
"""
from rest_framework import permissions


class IsVerifiedSeller(permissions.BasePermission):
    """
    Permission to check if user is a verified seller.
    Required for creating offers in marketplace.
    """
    
    message = "Seller verification required. Please complete phone and ID verification."
    
    def has_permission(self, request, view):
        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check phone verification
        if not hasattr(request.user, 'phone_verification') or not request.user.phone_verification.is_verified:
            self.message = "Phone number must be verified first"
            return False
        
        # Check seller verification
        if not hasattr(request.user, 'seller_verification'):
            self.message = "Seller verification required. Please submit your ID documents"
            return False
        
        verification = request.user.seller_verification
        
        if not verification.is_verified:
            if verification.status == 'PENDING':
                self.message = "Seller verification is pending review"
            elif verification.status == 'REJECTED':
                self.message = f"Seller verification was rejected: {verification.rejection_reason}"
            else:
                self.message = "Seller verification required"
            return False
        
        return True


class IsAdminOrSupport(permissions.BasePermission):
    """
    Permission for admin or support staff to review verifications.
    """
    
    message = "Admin or Support role required"
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is active and not banned
        if not request.user.is_active or request.user.is_banned:
            return False
        
        # Check if user is admin or support
        return request.user.role in ['ADMIN', 'SUPPORT'] or request.user.is_staff
