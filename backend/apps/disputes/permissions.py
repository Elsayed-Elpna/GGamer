"""
Dispute permissions.
"""
from rest_framework import permissions


class IsDisputeParticipant(permissions.BasePermission):
    """
    Permission: User must be participant in the dispute's order.
    """
    def has_object_permission(self, request, view, obj):
        # obj is Dispute
        return obj.order.is_participant(request.user) or request.user.is_staff


class IsAdminUser(permissions.BasePermission):
    """
    Permission: User must be staff/admin.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff
