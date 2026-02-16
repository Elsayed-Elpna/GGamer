"""
Order permissions.
"""
from rest_framework import permissions


class IsOrderParticipant(permissions.BasePermission):
    """
    Permission: User must be buyer or seller of the order.
    """
    def has_object_permission(self, request, view, obj):
        return obj.is_participant(request.user)


class IsOrderBuyer(permissions.BasePermission):
    """
    Permission: User must be the buyer.
    """
    def has_object_permission(self, request, view, obj):
        return obj.is_buyer(request.user)


class IsOrderSeller(permissions.BasePermission):
    """
    Permission: User must be the seller.
    """
    def has_object_permission(self, request, view, obj):
        return obj.is_seller(request.user)
