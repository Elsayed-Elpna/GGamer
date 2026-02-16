"""
Chat admin configuration.
"""
from django.contrib import admin
from apps.chat.models import (
    ChatRoom, ChatParticipant, ChatMessage, MessageAttachment, ChatAccessLog
)
from apps.chat.services.encryption_service import encryption_service


class ChatParticipantInline(admin.TabularInline):
    model = ChatParticipant
    extra = 0
    readonly_fields = ['user', 'role', 'can_send', 'joined_at']


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ['sender', 'get_decrypted_message', 'is_system', 'created_at']
    fields = ['sender', 'get_decrypted_message', 'is_system', 'created_at']
    can_delete = False
    
    def get_decrypted_message(self, obj):
        """Display decrypted message in admin."""
        return encryption_service.decrypt_message(obj.message_encrypted)
    get_decrypted_message.short_description = 'Message'


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'created_at', 'last_message_at']
    search_fields = ['order__id']
    readonly_fields = ['id', 'order', 'created_at', 'last_message_at']
    inlines = [ChatParticipantInline, ChatMessageInline]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ChatAccessLog)
class ChatAccessLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'chat_room', 'action', 'was_allowed', 'ip_address', 'created_at']
    list_filter = ['action', 'was_allowed', 'created_at']
    search_fields = ['user__email', 'chat_room__id', 'ip_address']
    readonly_fields = [
        'chat_room', 'user', 'action', 'ip_address', 'user_agent',
        'was_allowed', 'created_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
