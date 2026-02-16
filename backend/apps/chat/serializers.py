"""
Chat serializers.
Handles API input/output for chat operations.
"""
from rest_framework import serializers
from apps.chat.models import (
    ChatRoom, ChatParticipant, ChatMessage, MessageAttachment
)
from apps.chat.services.encryption_service import encryption_service


class ChatParticipantSerializer(serializers.ModelSerializer):
    """Serializer for chat participants."""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = ChatParticipant
        fields = ['id', 'user_email', 'role', 'can_send', 'joined_at']
        read_only_fields = fields


class MessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for message attachments."""
    
    class Meta:
        model = MessageAttachment
        fields = ['id', 'file', 'file_type', 'file_size', 'created_at']
        read_only_fields = ['id', 'file_type', 'file_size', 'created_at']


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages."""
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    message = serializers.SerializerMethodField()
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'sender_email', 'message', 'is_system',
            'attachments', 'created_at'
        ]
        read_only_fields = fields
    
    def get_message(self, obj):
        """Decrypt message for display."""
        return encryption_service.decrypt_message(obj.message_encrypted)


class ChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for chat room."""
    order_id = serializers.UUIDField(source='order.id', read_only=True)
    participants = ChatParticipantSerializer(many=True, read_only=True)
    recent_messages = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'order_id', 'participants', 'recent_messages',
            'created_at', 'last_message_at'
        ]
        read_only_fields = fields
    
    def get_recent_messages(self, obj):
        """Get last 10 messages."""
        messages = obj.messages.select_related('sender').prefetch_related(
            'attachments'
        ).order_by('-created_at')[:10]
        return ChatMessageSerializer(messages, many=True).data


class SendMessageSerializer(serializers.Serializer):
    """Serializer for sending messages."""
    message = serializers.CharField(max_length=5000)
    attachments = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        max_length=3,
        help_text="Max 3 attachments"
    )
    
    def validate_message(self, value):
        """Validate message is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        return value.strip()
    
    def validate_attachments(self, value):
        """Validate attachment files."""
        if not value:
            return []
        
        # Validate file sizes (max 5MB each)
        max_size = 5 * 1024 * 1024  # 5MB
        for file in value:
            if file.size > max_size:
                raise serializers.ValidationError(
                    f"File {file.name} exceeds max size of 5MB"
                )
        
        return value
