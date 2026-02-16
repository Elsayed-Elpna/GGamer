"""
Comprehensive tests for Orders app.
Tests all endpoints, services, and state machine.
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.orders.models import Order, EscrowAccount, OrderStateLog
from apps.marketplace.models import Offer, Game, MarketType, GameMarket

User = get_user_model()


class OrderAPITestCase(TestCase):
    """Test Order API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create users
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
        
        # Create marketplace data
        self.game = Game.objects.create(
            name='Test Game',
            slug='test-game'
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
            title='Test Offer',
            description='Test description',
            price=Decimal('100.00'),
            stock=10,
            delivery_time_hours=1,
            status='ACTIVE'
        )
    
    def test_create_order_success(self):
        """Test creating an order successfully."""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'offer_id': str(self.offer.id),
            'quantity': 2
        }
        
        response = self.client.post('/api/orders/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['buyer_email'], self.buyer.email)
        self.assertEqual(response.data['seller_email'], self.seller.email)
        self.assertEqual(response.data['state'], Order.CREATED)
        self.assertEqual(Decimal(response.data['total_amount']), Decimal('200.00'))
        
        # Verify escrow was created
        order = Order.objects.get(id=response.data['id'])
        self.assertTrue(hasattr(order, 'escrow'))
        self.assertEqual(order.escrow.total_amount, Decimal('200.00'))
    
    def test_create_order_unauthorized(self):
        """Test creating order without authentication."""
        data = {
            'offer_id': str(self.offer.id),
            'quantity': 1
        }
        
        response = self.client.post('/api/orders/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_order_insufficient_stock(self):
        """Test creating order with insufficient stock."""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'offer_id': str(self.offer.id),
            'quantity': 100  # More than available
        }
        
        response = self.client.post('/api/orders/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_order_state_transitions(self):
        """Test order state machine transitions."""
        # Create order
        order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            offer=self.offer,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            state=Order.CREATED
        )
        
        # Create escrow
        EscrowAccount.objects.create(
            order=order,
            total_amount=Decimal('100.00'),
            buyer_amount=Decimal('100.00')
        )
        
        # Test CREATED -> STARTED
        self.client.force_authenticate(user=self.seller)
        response = self.client.post(f'/api/orders/{order.id}/start/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        order.refresh_from_db()
        self.assertEqual(order.state, Order.STARTED)
        
        # Test STARTED -> DELIVERED
        response = self.client.post(
            f'/api/orders/{order.id}/deliver/',
            {'proof': 'Delivery proof text'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        order.refresh_from_db()
        self.assertEqual(order.state, Order.DELIVERED)
        
        # Test DELIVERED -> CONFIRMED
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(f'/api/orders/{order.id}/confirm/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        order.refresh_from_db()
        self.assertEqual(order.state, Order.CONFIRMED)
    
    def test_cancel_order(self):
        """Test cancelling an order."""
        order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            offer=self.offer,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            state=Order.CREATED
        )
        
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(
            f'/api/orders/{order.id}/cancel/',
            {'reason': 'Changed my mind'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        order.refresh_from_db()
        self.assertEqual(order.state, Order.CANCELLED)
    
    def test_list_orders_filtering(self):
        """Test listing orders with filtering."""
        # Create orders
        Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            offer=self.offer,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            state=Order.CREATED
        )
        
        Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            offer=self.offer,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            state=Order.CONFIRMED
        )
        
        self.client.force_authenticate(user=self.buyer)
        
        # Test all orders
        response = self.client.get('/api/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        # Test filtering by state
        response = self.client.get('/api/orders/?state=CREATED')
        self.assertEqual(len(response.data['results']), 1)


class OrderStateLogTestCase(TestCase):
    """Test order state logging."""
    
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
            total_amount=Decimal('100.00'),
            state=Order.CREATED
        )
    
    def test_state_change_logged(self):
        """Test that state changes are logged."""
        from apps.orders.services.state_machine import StateMachine
        
        initial_logs = OrderStateLog.objects.filter(order=self.order).count()
        
        # Transition state
        StateMachine.transition(
            order=self.order,
            to_state=Order.STARTED,
            user=self.seller,
            reason='Starting order'
        )
        
        # Check log was created
        new_logs = OrderStateLog.objects.filter(order=self.order).count()
        self.assertEqual(new_logs, initial_logs + 1)
        
        # Check log details
        log = OrderStateLog.objects.filter(order=self.order).latest('created_at')
        self.assertEqual(log.from_state, Order.CREATED)
        self.assertEqual(log.to_state, Order.STARTED)
        self.assertEqual(log.changed_by, self.seller)
