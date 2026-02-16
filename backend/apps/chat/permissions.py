"""
Chat permissions.
"""
from rest_framework import permissions
from apps.chat.services.chat_service import ChatService


class CanAccessChat(permissions.BasePermission):
    """
    Permission: User must have access to the chat room.
    """
    def has_object_permission(self, request, view, obj):
        # obj is ChatRoom
        return ChatService.can_access_chat(request.user, obj)


class CanSendMessage(permissions.BasePermission):
    """
    Permission: User must be able to send messages.
    """
    def has_object_permission(self, request, view, obj):
        # obj is ChatRoom
        return ChatService.can_send_message(request.user, obj)
