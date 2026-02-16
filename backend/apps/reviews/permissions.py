"""
Review permissions.
"""
from rest_framework import permissions


class IsOrderBuyer(permissions.BasePermission):
    """
    Permission: User must be the buyer of the order.
    """
    def has_permission(self, request, view):
        # Check in view
        return True
    
    def has_object_permission(self, request, view, obj):
        # obj is Order
        return obj.is_buyer(request.user)
