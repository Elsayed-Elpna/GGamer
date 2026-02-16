"""
Integration tests for complete buyer and seller journeys.
Tests end-to-end flows from registration to completion.
"""
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.marketplace.models import Game, MarketType, GameMarket, Offer
from apps.orders.models import Order
from apps.reviews.models import Review, SellerRating

User = get_user_model()


class BuyerJourneyTestCase(TestCase):
    """
    Test complete buyer journey from 0 to 100%.
    
    Journey:
    1. Register account
    2. Verify account
    3. Browse marketplace
    4. Create order
    5. Wait for delivery
    6. Confirm order
    7. Leave review
    """
    
    def setUp(self):
        """Set up marketplace data."""
        self.client = APIClient()
        
        # Create seller
        self.seller = User.objects.create_user(
            email='seller@test.com',
            password='testpass123',
            is_verified=True
        )
        
        # Create marketplace data
        self.game = Game.objects.create(
            name='Path of Exile',
            slug='path-of-exile'
        )
        self.market_type = MarketType.objects.create(
            name='Currency',
            slug='currency'
        )
        self.game_market = GameMarket.objects.create(
            game=self.game,
            market_type=self.market_type
        )
        
        # Create offer
        self.offer = Offer.objects.create(
            seller=self.seller,
            game_market=self.game_market,
            title='Divine Orbs x100',
            description='Fast delivery',
            price=Decimal('50.00'),
            stock=100,
            delivery_time_hours=1,
            status='ACTIVE'
        )
    
    def test_complete_buyer_journey(self):
        """Test complete buyer flow."""
        
        # 1. Register account  (simulated - would use accounts API)
        buyer = User.objects.create_user(
            email='buyer@test.com',
            password='testpass123',
            is_verified=True  # Simulating successful verification
        )
        
        # 2. Browse marketplace (public endpoint)
        # In real app: GET /api/marketplace/offers/
        # We'll skip this as marketplace API isn't built yet
        
        # 3. Create order
        self.client.force_authenticate(user=buyer)
        
        order_data = {
            'offer_id': str(self.offer.id),
            'quantity': 2
        }
        
        response = self.client.post('/api/orders/', order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        order_id = response.data['id']
        self.assertEqual(response.data['state'], Order.CREATED)
        self.assertEqual(Decimal(response.data['total_amount']), Decimal('100.00'))
        
        # 4. Seller starts order
        self.client.force_authenticate(user=self.seller)
        response = self.client.post(f'/api/orders/{order_id}/start/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['state'], Order.STARTED)
        
        # 5. Seller delivers order
        delivery_data = {
            'proof': 'Items delivered to buyer account. Screenshot attached.'
        }
        response = self.client.post(
            f'/api/orders/{order_id}/deliver/',
            delivery_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['state'], Order.DELIVERED)
        
        # 6. Buyer receives notification and confirms order
        self.client.force_authenticate(user=buyer)
        response = self.client.post(f'/api/orders/{order_id}/confirm/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['state'], Order.CONFIRMED)
        
        # 7. Buyer leaves review
        review_data = {
            'rating': 5,
            'delivery_speed': 5,
            'communication': 5,
            'as_described': 5,
            'comment': 'Great seller, fast delivery!'
        }
        
        response = self.client.post(
            f'/api/reviews/orders/{order_id}/create/',
            review_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rating'], 5)
        
        # Verify seller rating updated
        seller_rating = SellerRating.objects.get(seller=self.seller)
        self.assertEqual(seller_rating.total_reviews, 1)
        self.assertEqual(seller_rating.average_rating, Decimal('5.00'))
        
        # ✅ BUYER JOURNEY COMPLETE
        print("✅ Complete buyer journey: SUCCESS")


class SellerJourneyTestCase(TestCase):
    """
    Test complete seller journey from 0 to 100%.
    
    Journey:
    1. Register account
    2. Verify account
    3. Create offer
    4. Receive order
    5. Start order
    6. Deliver order
    7. Get paid (escrow release)
    """
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create buyer
        self.buyer = User.objects.create_user(
            email='buyer@test.com',
            password='testpass123',
            is_verified=True
        )
        
        # Create marketplace data
        self.game = Game.objects.create(
            name='Path of Exile',
            slug='path-of-exile'
        )
        self.market_type = MarketType.objects.create(
            name='Currency',
            slug='currency'
        )
        self.game_market = GameMarket.objects.create(
            game=self.game,
            market_type=self.market_type
        )
    
    def test_complete_seller_journey(self):
        """Test complete seller flow."""
        
        # 1. Register account (simulated)
        seller = User.objects.create_user(
            email='seller@test.com',
            password='testpass123',
            is_verified=True  # Simulating successful verification
        )
        
        # 2. Create offer
        # In real app: POST /api/marketplace/offers/
        offer = Offer.objects.create(
            seller=seller,
            game_market=self.game_market,
            title='Chaos Orbs x1000',
            description='Instant delivery',
            price=Decimal('25.00'),
            stock=50,
            delivery_time_hours=1,
            status='ACTIVE'
        )
        
        # 3. Buyer creates order
        self.client.force_authenticate(user=self.buyer)
        
        order_data = {
            'offer_id': str(offer.id),
            'quantity': 4
        }
        
        response = self.client.post('/api/orders/', order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        order_id = response.data['id']
        total_amount = Decimal(response.data['total_amount'])
        self.assertEqual(total_amount, Decimal('100.00'))
        
        # 4. Seller receives notification and starts order
        self.client.force_authenticate(user=seller)
        response = self.client.post(f'/api/orders/{order_id}/start/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 5. Seller delivers order
        delivery_data = {
            'proof': 'Delivered 4000 Chaos Orbs to buyer. Trade ID: CH-1234'
        }
        
        response = self.client.post(
            f'/api/orders/{order_id}/deliver/',
            delivery_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['state'], Order.DELIVERED)
        
        # 6. Buyer confirms
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(f'/api/orders/{order_id}/confirm/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['state'], Order.CONFIRMED)
        
        # 7. Verify escrow released to seller
        from apps.orders.models import EscrowAccount
        
        order = Order.objects.get(id=order_id)
        escrow = order.escrow
        self.assertEqual(escrow.status, EscrowAccount.RELEASED)
        
        # ✅ SELLER JOURNEY COMPLETE
        print("✅ Complete seller journey: SUCCESS")


class DisputeJourneyTestCase(TestCase):
    """Test dispute resolution journey."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.buyer = User.objects.create_user(
            email='buyer@test.com',
            password='testpass123',
            is_verified=True
        )
        self.seller = User.objects.create_user(
            email='seller@test.com',
            password='testpass123',
            is_verified=True
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
        from apps.orders.models import EscrowAccount
        EscrowAccount.objects.create(
            order=self.order,
            total_amount=Decimal('100.00'),
            buyer_amount=Decimal('100.00'),
            status=EscrowAccount.HELD
        )
    
    def test_dispute_journey_buyer_wins(self):
        """Test dispute where buyer wins."""
        
        # 1. Buyer creates dispute
        self.client.force_authenticate(user=self.buyer)
        
        dispute_data = {
            'reason': 'Wrong items delivered',
            'description': 'Seller sent Chaos Orbs instead of Divine Orbs'
        }
        
        response = self.client.post(
            f'/api/disputes/orders/{self.order.id}/create/',
            dispute_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        dispute_id = response.data['id']
        
        # 2. Buyer uploads evidence
        from django.core.files.uploadedfile import SimpleUploadedFile
        evidence_file = SimpleUploadedFile(
            "evidence.txt",
            b"Screenshot showing wrong items",
            content_type="text/plain"
        )
        
        response = self.client.post(
            f'/api/disputes/{dispute_id}/evidence/',
            {'file': evidence_file, 'description': 'Proof of wrong items'},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 3. Admin reviews and refunds buyer
        self.client.force_authenticate(user=self.admin)
        
        decision_data = {
            'reason': 'Evidence confirms wrong items were sent'
        }
        
        response = self.client.post(
            f'/api/disputes/{dispute_id}/admin/refund-buyer/',
            decision_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify order refunded
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, Order.REFUNDED)
        
        # ✅ DISPUTE JOURNEY COMPLETE
        print("✅ Dispute journey (buyer wins): SUCCESS")


class ChatJourneyTestCase(TestCase):
    """Test chat communication journey."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
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
            total_amount=Decimal('100.00'),
            state=Order.CREATED
        )
    
    def test_chat_journey(self):
        """Test complete chat flow."""
        
        # 1. Buyer accesses chat
        self.client.force_authenticate(user=self.buyer)
        
        response = self.client.get(f'/api/chat/orders/{self.order.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 2. Buyer sends message
        message_data = {
            'message': 'When will you deliver?'
        }
        
        response = self.client.post(
            f'/api/chat/orders/{self.order.id}/send/',
            message_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'When will you deliver?')
        
        # 3. Seller replies
        self.client.force_authenticate(user=self.seller)
        
        reply_data = {
            'message': 'Within 1 hour!'
        }
        
        response = self.client.post(
            f'/api/chat/orders/{self.order.id}/send/',
            reply_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 4. Both can see messages
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(f'/api/chat/orders/{self.order.id}/messages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # ✅ CHAT JOURNEY COMPLETE
        print("✅ Chat journey: SUCCESS")
