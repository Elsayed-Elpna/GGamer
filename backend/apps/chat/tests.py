"""
Comprehensive tests for Chat app.
Tests encryption, access control, and messaging.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.chat.models import ChatRoom, ChatMessage, ChatParticipant
from apps.chat.services.encryption_service import encryption_service
from apps.chat.services.chat_service import ChatService
from apps.orders.models import Order
from decimal import Decimal

User = get_user_model()


class ChatAPITestCase(TestCase):
    """Test Chat API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create users
        self.buyer = User.objects.create_user(
            email='buyer@test.com',
            password='testpass123'
        )
        self.seller = User.objects.create_user(
            email='seller@test.com',
            password='testpass123'
        )
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        
        # Create order
        self.order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            state=Order.CREATED
        )
        
        # Create chat room
        self.chat_room = ChatService.get_or_create_chat_room(self.order)
    
    def test_get_chat_room_as_buyer(self):
        """Test buyer can access chat room."""
        self.client.force_authenticate(user=self.buyer)
        
        response = self.client.get(f'/api/chat/orders/{self.order.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['order_id'], str(self.order.id))
        self.assertEqual(len(response.data['participants']), 2)
    
    def test_get_chat_room_unauthorized(self):
        """Test unauthorized user cannot access chat."""
        other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=other_user)
        
        response = self.client.get(f'/api/chat/orders/{self.order.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_send_message(self):
        """Test sending a message."""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'message': 'Hello seller!'
        }
        
        response = self.client.post(
            f'/api/chat/orders/{self.order.id}/send/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'Hello seller!')
        self.assertEqual(response.data['sender_email'], self.buyer.email)
        
        # Verify message is encrypted in DB
        message = ChatMessage.objects.get(id=response.data['id'])
        self.assertNotEqual(message.message_encrypted, b'Hello seller!')
        
        # Verify decryption works
        decrypted = encryption_service.decrypt_message(message.message_encrypted)
        self.assertEqual(decrypted, 'Hello seller!')
    
    def test_get_messages(self):
        """Test retrieving messages."""
        # Send a message
        ChatService.send_message(
            chat_room=self.chat_room,
            sender=self.buyer,
            message='Test message',
            ip_address='127.0.0.1'
        )
        
        self.client.force_authenticate(user=self.buyer)
        
        response = self.client.get(f'/api/chat/orders/{self.order.id}/messages/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['message'], 'Test message')
    
    def test_admin_read_only_access(self):
        """Test admin gets read-only access."""
        self.client.force_authenticate(user=self.admin)
        
        # Admin can view chat
        response = self.client.get(f'/api/chat/orders/{self.order.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify admin was added as participant
        participant = ChatParticipant.objects.get(
            chat_room=self.chat_room,
            user=self.admin
        )
        self.assertFalse(participant.can_send)  # Read-only
    
    def test_message_encryption(self):
        """Test message encryption service."""
        message = "Secret message"
        
        # Encrypt
        encrypted = encryption_service.encrypt_message(message)
        self.assertIsInstance(encrypted, bytes)
        self.assertNotEqual(encrypted, message.encode())
        
        # Decrypt
        decrypted = encryption_service.decrypt_message(encrypted)
        self.assertEqual(decrypted, message)


class ChatAccessLogTestCase(TestCase):
    """Test chat access logging."""
    
    def setUp(self):
        """Set up test data."""
        self.buyer = User.objects.create_user(
            email='buyer@test.com',
            password='testpass123'
        )
        self.seller = User.objects.create_user(
            email='seller@test.com',
            password='testpass123'
        )
        
        self.order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        
        self.chat_room = ChatService.get_or_create_chat_room(self.order)
    
    def test_access_logged(self):
        """Test that chat access is logged."""
        from apps.chat.models import ChatAccessLog
        
        initial_logs = ChatAccessLog.objects.count()
        
        # Access chat
        ChatService.get_messages(
            chat_room=self.chat_room,
            user=self.buyer,
            ip_address='127.0.0.1'
        )
        
        # Check log was created
        new_logs = ChatAccessLog.objects.count()
        self.assertEqual(new_logs, initial_logs + 1)
        
        # Check log details
        log = ChatAccessLog.objects.latest('created_at')
        self.assertEqual(log.user, self.buyer)
        self.assertEqual(log.action, 'view_messages')
        self.assertTrue(log.was_allowed)
