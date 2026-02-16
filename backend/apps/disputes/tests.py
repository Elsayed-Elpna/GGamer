"""
Comprehensive tests for Disputes app.
Tests dispute creation, evidence, and admin decisions.
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.disputes.models import Dispute, DisputeEvidence, DisputeDecision
from apps.disputes.services.dispute_service import DisputeService
from apps.orders.models import Order, EscrowAccount

User = get_user_model()


class DisputeAPITestCase(TestCase):
    """Test Dispute API endpoints."""
    
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
            state=Order.DELIVERED
        )
        
        # Create escrow
        self.escrow = EscrowAccount.objects.create(
            order=self.order,
            total_amount=Decimal('100.00'),
            buyer_amount=Decimal('100.00'),
            status=EscrowAccount.HELD
        )
    
    def test_create_dispute_as_buyer(self):
        """Test buyer can create dispute."""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'reason': 'Item not as described',
            'description': 'The seller sent wrong items.'
        }
        
        response = self.client.post(
            f'/api/disputes/orders/{self.order.id}/create/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['created_by_role'], Dispute.BUYER)
        self.assertEqual(response.data['status'], Dispute.OPEN)
        
        # Verify order transitioned to DISPUTED
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, Order.DISPUTED)
    
    def test_create_dispute_unauthorized(self):
        """Test non-participant cannot create dispute."""
        other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=other_user)
        
        data = {
            'reason': 'Test',
            'description': 'Test description'
        }
        
        response = self.client.post(
            f'/api/disputes/orders/{self.order.id}/create/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_upload_evidence(self):
        """Test uploading evidence."""
        # Create dispute
        dispute = DisputeService.create_dispute(
            order=self.order,
            user=self.buyer,
            reason='Test',
            description='Test description'
        )
        
        self.client.force_authenticate(user=self.buyer)
        
        # Create a test file
        from django.core.files.uploadedfile import SimpleUploadedFile
        test_file = SimpleUploadedFile(
            "evidence.txt",
            b"Test evidence content",
            content_type="text/plain"
        )
        
        data = {
            'file': test_file,
            'description': 'Screenshot showing issue'
        }
        
        response = self.client.post(
            f'/api/disputes/{dispute.id}/evidence/',
            data,
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('file', response.data)
    
    def test_admin_refund_buyer(self):
        """Test admin can refund buyer."""
        # Create dispute
        dispute = DisputeService.create_dispute(
            order=self.order,
            user=self.buyer,
            reason='Scam',
            description='Seller scammed me'
        )
        
        self.client.force_authenticate(user=self.admin)
        
        data = {
            'reason': 'Seller failed to deliver correct item'
        }
        
        response = self.client.post(
            f'/api/disputes/{dispute.id}/admin/refund-buyer/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['decision_type'], DisputeDecision.REFUND_BUYER)
        
        # Verify dispute resolved
        dispute.refresh_from_db()
        self.assertEqual(dispute.status, Dispute.RESOLVED)
        
        # Verify order refunded
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, Order.REFUNDED)
    
    def test_admin_partial_refund(self):
        """Test admin can do partial refund."""
        dispute = DisputeService.create_dispute(
            order=self.order,
            user=self.buyer,
            reason='Partial delivery',
            description='Only got 50% of items'
        )
        
        self.client.force_authenticate(user=self.admin)
        
        data = {
            'buyer_amount': '50.00',
            'seller_amount': '50.00',
            'reason': 'Partial delivery confirmed'
        }
        
        response = self.client.post(
            f'/api/disputes/{dispute.id}/admin/partial-refund/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Decimal(response.data['buyer_refund_amount']),
            Decimal('50.00')
        )
        self.assertEqual(
            Decimal(response.data['seller_release_amount']),
            Decimal('50.00')
        )
    
    def test_admin_ban_seller(self):
        """Test admin can ban seller."""
        dispute = DisputeService.create_dispute(
            order=self.order,
            user=self.buyer,
            reason='Scam',
            description='Repeated scam attempts'
        )
        
        self.client.force_authenticate(user=self.admin)
        
        data = {
            'reason': 'Multiple scam reports confirmed'
        }
        
        response = self.client.post(
            f'/api/disputes/{dispute.id}/admin/ban-seller/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify seller banned
        self.seller.refresh_from_db()
        self.assertFalse(self.seller.is_active)
        
        # Verify buyer refunded
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, Order.REFUNDED)
