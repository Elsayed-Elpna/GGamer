"""
Chat service - main business logic for chat operations.
Handles chat room creation, messaging, and access control.
"""
from typing import Optional, List
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from apps.chat.models import (
    ChatRoom, ChatParticipant, ChatMessage, MessageAttachment, ChatAccessLog
)
from apps.chat.services.encryption_service import encryption_service
from apps.orders.models import Order
from apps.accounts.models import User


class ChatService:
    """
    Service for managing chat operations.
    Handles access control, encryption, and audit logging.
    """
    
    @staticmethod
    @transaction.atomic
    def get_or_create_chat_room(order: Order) -> ChatRoom:
        """
        Get or create chat room for an order.
        Automatically adds buyer and seller as participants.
        
        Args:
            order: Order to create chat for
            
        Returns:
            ChatRoom instance
        """
        # Get or create chat room
        chat_room, created = ChatRoom.objects.get_or_create(order=order)
        
        if created:
            # Add buyer as participant
            ChatParticipant.objects.create(
                chat_room=chat_room,
                user=order.buyer,
                role=ChatParticipant.BUYER,
                can_send=True
            )
            
            # Add seller as participant
            ChatParticipant.objects.create(
                chat_room=chat_room,
                user=order.seller,
                role=ChatParticipant.SELLER,
                can_send=True
            )
        
        return chat_room
    
    @staticmethod
    def can_access_chat(user: User, chat_room: ChatRoom) -> bool:
        """
        Check if user can access chat room.
        
        Args:
            user: User attempting access
            chat_room: Chat room to access
            
        Returns:
            True if user can access
        """
        # Check if user is participant
        if ChatParticipant.objects.filter(
            chat_room=chat_room,
            user=user
        ).exists():
            return True
        
        # Check if user is admin/staff
        if user.is_staff:
            return True
        
        return False
    
    @staticmethod
    def can_send_message(user: User, chat_room: ChatRoom) -> bool:
        """
        Check if user can send messages in chat room.
        
        Args:
            user: User attempting to send
            chat_room: Chat room
            
        Returns:
            True if user can send
        """
        try:
            participant = ChatParticipant.objects.get(
                chat_room=chat_room,
                user=user
            )
            return participant.can_send
        except ChatParticipant.DoesNotExist:
            return False
    
    @staticmethod
    @transaction.atomic
    def send_message(
        chat_room: ChatRoom,
        sender: User,
        message: str,
        attachments: Optional[List] = None,
        ip_address: Optional[str] = None
    ) -> ChatMessage:
        """
        Send a message in chat room.
        
        Security:
        - Validates sender has permission
        - Encrypts message
        - Logs access
        
        Args:
            chat_room: Chat room to send in
            sender: User sending message
            message: Plain text message
            attachments: Optional list of file attachments
            ip_address: Sender IP address
            
        Returns:
            Created ChatMessage
        """
        # Validate sender can send
        if not ChatService.can_send_message(sender, chat_room):
            # Log unauthorized attempt
            ChatAccessLog.objects.create(
                chat_room=chat_room,
                user=sender,
                action='send_message',
                ip_address=ip_address,
                was_allowed=False
            )
            raise PermissionDenied("You cannot send messages in this chat")
        
        # Encrypt message
        encrypted = encryption_service.encrypt_message(message)
        message_hash = ChatMessage.generate_hash(message)
        
        # Create message
        chat_message = ChatMessage.objects.create(
            chat_room=chat_room,
            sender=sender,
            message_encrypted=encrypted,
            message_hash=message_hash,
            is_system=False
        )
        
        # Add attachments
        if attachments:
            for file in attachments:
                MessageAttachment.objects.create(
                    message=chat_message,
                    file=file,
                    file_type=file.content_type,
                    file_size=file.size
                )
        
        # Update last message time
        chat_room.last_message_at = timezone.now()
        chat_room.save()
        
        # Log access
        ChatAccessLog.objects.create(
            chat_room=chat_room,
            user=sender,
            action='send_message',
            ip_address=ip_address,
            was_allowed=True
        )
        
        return chat_message
    
    @staticmethod
    def get_messages(
        chat_room: ChatRoom,
        user: User,
        ip_address: Optional[str] = None
    ) -> List[ChatMessage]:
        """
        Get messages from chat room.
        
        Security:
        - Validates user has access
        - Logs access attempt
        
        Args:
            chat_room: Chat room to get messages from
            user: User requesting messages
            ip_address: User IP address
            
        Returns:
            List of ChatMessage instances
        """
        # Validate access
        if not ChatService.can_access_chat(user, chat_room):
            # Log unauthorized attempt
            ChatAccessLog.objects.create(
                chat_room=chat_room,
                user=user,
                action='view_messages',
                ip_address=ip_address,
                was_allowed=False
            )
            raise PermissionDenied("You cannot access this chat")
        
        # Log access
        ChatAccessLog.objects.create(
            chat_room=chat_room,
            user=user,
            action='view_messages',
            ip_address=ip_address,
            was_allowed=True
        )
        
        # Get messages
        return chat_room.messages.select_related('sender').prefetch_related(
            'attachments'
        ).all()
    
    @staticmethod
    @transaction.atomic
    def add_support_to_chat(
        chat_room: ChatRoom,
        support_user: User,
        can_send: bool = True
    ) -> ChatParticipant:
        """
        Add support/admin user to chat.
        
        Args:
            chat_room: Chat room
            support_user: Support/admin user to add
            can_send: Whether user can send (False for read-only)
            
        Returns:
            Created ChatParticipant
        """
        if not support_user.is_staff:
            raise PermissionDenied("Only staff can be added as support")
        
        # Determine role
        role = ChatParticipant.ADMIN if support_user.is_superuser else ChatParticipant.SUPPORT
        
        # Add participant (or update existing)
        participant, created = ChatParticipant.objects.get_or_create(
            chat_room=chat_room,
            user=support_user,
            defaults={
                'role': role,
                'can_send': can_send
            }
        )
        
        if not created:
            participant.role = role
            participant.can_send = can_send
            participant.save()
        
        return participant
    
    @staticmethod
    def create_system_message(
        chat_room: ChatRoom,
        message: str
    ) -> ChatMessage:
        """
        Create system message (e.g., "Order was delivered").
        
        Args:
            chat_room: Chat room
            message: System message text
            
        Returns:
            Created ChatMessage
        """
        encrypted = encryption_service.encrypt_message(message)
        message_hash = ChatMessage.generate_hash(message)
        
        return ChatMessage.objects.create(
            chat_room=chat_room,
            sender=None,  # System message has no sender
            message_encrypted=encrypted,
            message_hash=message_hash,
            is_system=True
        )
