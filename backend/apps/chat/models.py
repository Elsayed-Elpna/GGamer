"""
Chat models - Order-based messaging with encryption.
Production-ready with security and audit trails.
"""
import uuid
import hashlib
from django.db import models
from django.core.validators import FileExtensionValidator
from apps.accounts.models import User
from apps.orders.models import Order


class ChatRoom(models.Model):
    """
    Chat room linked to an order.
    One chat room per order.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='chat_room'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Chat Room'
        verbose_name_plural = 'Chat Rooms'
    
    def __str__(self):
        return f"Chat for Order {self.order.id}"


class ChatParticipant(models.Model):
    """
    Participants in a chat room.
    Defines who can access the chat and their permissions.
    """
    # Participant roles
    BUYER = 'BUYER'
    SELLER = 'SELLER'
    ADMIN = 'ADMIN'
    SUPPORT = 'SUPPORT'
    
    ROLE_CHOICES = [
        (BUYER, 'Buyer'),
        (SELLER, 'Seller'),
        (ADMIN, 'Admin'),
        (SUPPORT, 'Support'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_participations'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    can_send = models.BooleanField(
        default=True,
        help_text="False for admin read-only access"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Chat Participant'
        verbose_name_plural = 'Chat Participants'
        unique_together = [['chat_room', 'user']]
        indexes = [
            models.Index(fields=['chat_room', 'user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.role} in {self.chat_room}"


class ChatMessage(models.Model):
    """
    Encrypted chat message.
    Messages are encrypted at rest for privacy.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chat_messages'
    )
    
    # Encrypted message
    message_encrypted = models.BinaryField(
        help_text="Encrypted message content"
    )
    message_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 hash for deduplication"
    )
    
    # System messages (e.g., "Order was delivered")
    is_system = models.BooleanField(
        default=False,
        help_text="System-generated message"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat Messages'
        indexes = [
            models.Index(fields=['chat_room', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]
    
    def __str__(self):
        return f"Message in {self.chat_room} at {self.created_at}"
    
    @staticmethod
    def generate_hash(message: str) -> str:
        """Generate SHA-256 hash of message for deduplication."""
        return hashlib.sha256(message.encode()).hexdigest()


class MessageAttachment(models.Model):
    """
    File attachments for chat messages.
    Supports images and documents.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(
        upload_to='chat_attachments/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'pdf', 'txt']
            )
        ]
    )
    file_type = models.CharField(max_length=50)
    file_size = models.IntegerField(help_text="File size in bytes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Message Attachment'
        verbose_name_plural = 'Message Attachments'
    
    def __str__(self):
        return f"Attachment for message {self.message.id}"


class ChatAccessLog(models.Model):
    """
    Audit log for chat access.
    Logs all chat room access attempts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='access_logs'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    action = models.CharField(
        max_length=50,
        help_text="Action: view, send_message, etc."
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    was_allowed = models.BooleanField(
        default=True,
        help_text="Whether access was granted"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Chat Access Log'
        verbose_name_plural = 'Chat Access Logs'
        indexes = [
            models.Index(fields=['chat_room', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} on {self.chat_room} at {self.created_at}"
