"""
Comprehensive tests for Reviews app.
Tests review creation, fake review detection, and rating updates.
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.reviews.models import Review, SellerRating
from apps.reviews.services.review_service import ReviewService
from apps.orders.models import Order

User = get_user_model()


class ReviewAPITestCase(TestCase):
    """Test Review API endpoints."""
    
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
        
        # Create confirmed order
        self.order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            state=Order.CONFIRMED  # Must be confirmed
        )
    
    def test_create_review_success(self):
        """Test buyer can create review."""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'rating': 5,
            'delivery_speed': 5,
            'communication': 4,
            'as_described': 5,
            'comment': 'Great seller!'
        }
        
        response = self.client.post(
            f'/api/reviews/orders/{self.order.id}/create/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rating'], 5)
        self.assertEqual(response.data['buyer_email'], self.buyer.email)
        self.assertEqual(response.data['seller_email'], self.seller.email)
        
        # Verify seller rating was updated
        seller_rating = SellerRating.objects.get(seller=self.seller)
        self.assertEqual(seller_rating.total_reviews, 1)
        self.assertEqual(seller_rating.average_rating, Decimal('5.00'))
    
    def test_create_review_order_not_confirmed(self):
        """Test cannot review non-confirmed order."""
        # Create non-confirmed order
        order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            state=Order.CREATED  # Not confirmed
        )
        
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'rating': 5,
            'delivery_speed': 5,
            'communication': 5,
            'as_described': 5
        }
        
        response = self.client.post(
            f'/api/reviews/orders/{order.id}/create/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_create_review_not_buyer(self):
        """Test only buyer can create review."""
        self.client.force_authenticate(user=self.seller)
        
        data = {
            'rating': 5,
            'delivery_speed': 5,
            'communication': 5,
            'as_described': 5
        }
        
        response = self.client.post(
            f'/api/reviews/orders/{self.order.id}/create/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_duplicate_review_prevented(self):
        """Test cannot review same order twice."""
        # Create first review
        ReviewService.create_review(
            order=self.order,
            buyer=self.buyer,
            rating=5,
            delivery_speed=5,
            communication=5,
            as_described=5
        )
        
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'rating': 4,
            'delivery_speed': 4,
            'communication': 4,
            'as_described': 4
        }
        
        response = self.client.post(
            f'/api/reviews/orders/{self.order.id}/create/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_seller_reviews(self):
        """Test getting seller reviews."""
        # Create multiple reviews
        for i in range(3):
            order = Order.objects.create(
                buyer=self.buyer,
                seller=self.seller,
                quantity=1,
                unit_price=Decimal('100.00'),
                total_amount=Decimal('100.00'),
                state=Order.CONFIRMED
            )
            ReviewService.create_review(
                order=order,
                buyer=self.buyer,
                rating=5,
                delivery_speed=5,
                communication=5,
                as_described=5
            )
        
        # No authentication needed for public endpoint
        response = self.client.get(f'/api/reviews/sellers/{self.seller.id}/reviews/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
    
    def test_get_seller_rating(self):
        """Test getting seller rating statistics."""
        # Create reviews with different ratings
        ratings = [5, 4, 5, 3, 5]
        
        for rating in ratings:
            order = Order.objects.create(
                buyer=self.buyer,
                seller=self.seller,
                quantity=1,
                unit_price=Decimal('100.00'),
                total_amount=Decimal('100.00'),
                state=Order.CONFIRMED
            )
            ReviewService.create_review(
                order=order,
                buyer=self.buyer,
                rating=rating,
                delivery_speed=rating,
                communication=rating,
                as_described=rating
            )
        
        response = self.client.get(f'/api/reviews/sellers/{self.seller.id}/rating/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_reviews'], 5)
        self.assertEqual(response.data['five_star_count'], 3)
        self.assertEqual(response.data['four_star_count'], 1)
        self.assertEqual(response.data['three_star_count'], 1)
        
        # Check average (5+4+5+3+5)/5 = 4.4
        self.assertEqual(Decimal(response.data['average_rating']), Decimal('4.40'))


class FakeReviewDetectionTestCase(TestCase):
    """Test fake review detection."""
    
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
    
    def test_same_ip_multiple_reviews_blocked(self):
        """Test same IP cannot create multiple reviews for same seller."""
        ip_address = '192.168.1.1'
        
        # Create 3 reviews from same IP
        for i in range(3):
            order = Order.objects.create(
                buyer=self.buyer,
                seller=self.seller,
                quantity=1,
                unit_price=Decimal('100.00'),
                total_amount=Decimal('100.00'),
                state=Order.CONFIRMED
            )
            ReviewService.create_review(
                order=order,
                buyer=self.buyer,
                rating=5,
                delivery_speed=5,
                communication=5,
                as_described=5,
                ip_address=ip_address
            )
        
        # 4th review should be blocked
        order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            quantity=1,
            unit_price=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            state=Order.CONFIRMED
        )
        
        with self.assertRaises(Exception):
            ReviewService.create_review(
                order=order,
                buyer=self.buyer,
                rating=5,
                delivery_speed=5,
                communication=5,
                as_described=5,
                ip_address=ip_address
            )
