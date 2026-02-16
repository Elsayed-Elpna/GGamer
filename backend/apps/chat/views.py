"""
Chat views and API endpoints.
Production-ready with encryption, access control, and audit logging.
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.chat.models import ChatRoom
from apps.chat.serializers import (
    ChatRoomSerializer,
    ChatMessageSerializer,
    SendMessageSerializer
)
from apps.chat.permissions import CanAccessChat, CanSendMessage
from apps.chat.services.chat_service import ChatService
from apps.orders.models import Order
from apps.verification.utils import get_client_ip


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_order_chat(request, order_id):
    """
    Get or create chat room for an order.
    
    Security:
    - Only order participants and staff can access
    - Access is logged
    """
    # Get order
    order = get_object_or_404(Order, id=order_id)
    
    # Check if user can access this order
    if not (order.is_participant(request.user) or request.user.is_staff):
        return Response(
            {'error': 'You do not have access to this order'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get or create chat room
    chat_room = ChatService.get_or_create_chat_room(order)
    
    # If user is staff, add them as participant
    if request.user.is_staff and not ChatService.can_access_chat(request.user, chat_room):
        ChatService.add_support_to_chat(
            chat_room=chat_room,
            support_user=request.user,
            can_send=False  # Admin read-only by default
        )
    
    # Serialize and return
    serializer = ChatRoomSerializer(chat_room)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_chat_messages(request, order_id):
    """
    Get messages from order chat.
    
    Security:
    - Access control via ChatService
    - All access logged
    """
    # Get order and chat room
    order = get_object_or_404(Order, id=order_id)
    
    try:
        chat_room = order.chat_room
    except ChatRoom.DoesNotExist:
        return Response(
            {'error': 'Chat room does not exist for this order'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        ip_address = get_client_ip(request)
        messages = ChatService.get_messages(
            chat_room=chat_room,
            user=request.user,
            ip_address=ip_address
        )
        
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_message(request, order_id):
    """
    Send message in order chat.
    
    Security:
    - Permission check via ChatService
    - Message encrypted before storage
    - Access logged
    """
    # Get order and chat room
    order = get_object_or_404(Order, id=order_id)
    
    try:
        chat_room = order.chat_room
    except ChatRoom.DoesNotExist:
        # Create chat room if doesn't exist
        chat_room = ChatService.get_or_create_chat_room(order)
    
    # Validate input
    serializer = SendMessageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ip_address = get_client_ip(request)
        
        # Send message
        message = ChatService.send_message(
            chat_room=chat_room,
            sender=request.user,
            message=serializer.validated_data['message'],
            attachments=serializer.validated_data.get('attachments', []),
            ip_address=ip_address
        )
        
        # Return created message
        response_serializer = ChatMessageSerializer(message)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_support_to_chat(request, order_id):
    """
    Add support user to chat (admin only).
    
    Allows admins to add themselves or other support staff to chats.
    """
    if not request.user.is_staff:
        return Response(
            {'error': 'Only staff can add support to chats'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get order and chat room
    order = get_object_or_404(Order, id=order_id)
    
    try:
        chat_room = order.chat_room
    except ChatRoom.DoesNotExist:
        chat_room = ChatService.get_or_create_chat_room(order)
    
    # Add current user as support
    try:
        participant = ChatService.add_support_to_chat(
            chat_room=chat_room,
            support_user=request.user,
            can_send=request.data.get('can_send', False)  # Read-only by default
        )
        
        from apps.chat.serializers import ChatParticipantSerializer
        serializer = ChatParticipantSerializer(participant)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
