"""
Review service - business logic for reviews and ratings.
Handles review creation, validation, and seller rating updates.
"""
from typing import Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Avg, Count
from apps.reviews.models import Review, SellerRating
from apps.orders.models import Order
from apps.accounts.models import User


class ReviewService:
    """
    Service for managing reviews and seller ratings.
    Includes fake review detection and automatic rating updates.
    """
    
    @staticmethod
    @transaction.atomic
    def create_review(
        order: Order,
        buyer: User,
        rating: int,
        delivery_speed: int,
        communication: int,
        as_described: int,
        comment: str = "",
        ip_address: Optional[str] = None,
        user_agent: str = ""
    ) -> Review:
        """
        Create a review for a completed order.
        
        Security:
        - Only buyer can review
        - Order must be CONFIRMED
        - One review per order
        - Fake review detection
        
        Args:
            order: Order to review
            buyer: Buyer creating review
            rating: Overall rating (1-5)
            delivery_speed: Speed rating (1-5)
            communication: Communication rating (1-5)
            as_described: Accuracy rating (1-5)
            comment: Optional comment
            ip_address: Buyer IP
            user_agent: Browser/app info
            
        Returns:
            Created Review
        """
        # Validate buyer
        if not order.is_buyer(buyer):
            raise PermissionDenied("Only the buyer can review this order")
        
        # Validate order status
        if order.state != Order.CONFIRMED:
            raise ValidationError("Can only review CONFIRMED orders")
        
        # Check for existing review
        if hasattr(order, 'review'):
            raise ValidationError("Order already has a review")
        
        # Fake review detection
        ReviewService._detect_fake_review(buyer, order.seller, ip_address)
        
        # Create review
        review = Review.objects.create(
            order=order,
            buyer=buyer,
            seller=order.seller,
            rating=rating,
            delivery_speed=delivery_speed,
            communication=communication,
            as_described=as_described,
            comment=comment[:1000],
            ip_address=ip_address,
            user_agent=user_agent[:500]
        )
        
        # Update seller rating
        ReviewService.update_seller_rating(order.seller)
        
        return review
    
    @staticmethod
    def _detect_fake_review(
        buyer: User,
        seller: User,
        ip_address: Optional[str]
    ) -> None:
        """
        Detect potential fake reviews.
        
        Checks:
        - Same user reviewing same seller multiple times from same IP
        - Excessive reviews from same IP
        
        Raises:
            ValidationError if fake review detected
        """
        if not ip_address:
            return
        
        # Check if same IP reviewed this seller recently (within 1 day)
        from django.utils import timezone
        from datetime import timedelta
        
        recent_reviews = Review.objects.filter(
            seller=seller,
            ip_address=ip_address,
            created_at__gte=timezone.now() - timedelta(days=1)
        ).count()
        
        if recent_reviews >= 3:
            raise ValidationError(
                "Multiple reviews from same IP detected. Please contact support."
            )
        
        # Check if buyer has multiple reviews from same IP
        buyer_reviews_same_ip = Review.objects.filter(
            buyer=buyer,
            ip_address=ip_address
        ).count()
        
        if buyer_reviews_same_ip >= 5:
            raise ValidationError(
                "Suspicious review pattern detected. Please contact support."
            )
    
    @staticmethod
    @transaction.atomic
    def update_seller_rating(seller: User) -> SellerRating:
        """
        Update seller's aggregate rating.
        Recalculates all statistics.
        
        Args:
            seller: Seller to update
            
        Returns:
            Updated SellerRating
        """
        # Get or create seller rating
        seller_rating, created = SellerRating.objects.get_or_create(
            seller=seller
        )
        
        # Get all reviews for seller
        reviews = Review.objects.filter(seller=seller)
        
        # Calculate aggregates
        stats = reviews.aggregate(
            total=Count('id'),
            avg_rating=Avg('rating'),
            avg_delivery=Avg('delivery_speed'),
            avg_comm=Avg('communication'),
            avg_described=Avg('as_described')
        )
        
        # Update totals
        seller_rating.total_reviews = stats['total'] or 0
        seller_rating.average_rating = Decimal(str(stats['avg_rating'] or 0)).quantize(Decimal('0.01'))
        seller_rating.average_delivery_speed = Decimal(str(stats['avg_delivery'] or 0)).quantize(Decimal('0.01'))
        seller_rating.average_communication = Decimal(str(stats['avg_comm'] or 0)).quantize(Decimal('0.01'))
        seller_rating.average_as_described = Decimal(str(stats['avg_described'] or 0)).quantize(Decimal('0.01'))
        
        # Star breakdown
        seller_rating.five_star_count = reviews.filter(rating=5).count()
        seller_rating.four_star_count = reviews.filter(rating=4).count()
        seller_rating.three_star_count = reviews.filter(rating=3).count()
        seller_rating.two_star_count = reviews.filter(rating=2).count()
        seller_rating.one_star_count = reviews.filter(rating=1).count()
        
        # Calculate delivery rate
        total_orders = Order.objects.filter(seller=seller).exclude(
            state__in=[Order.CREATED, Order.CANCELLED]
        ).count()
        
        confirmed_orders = Order.objects.filter(
            seller=seller,
            state=Order.CONFIRMED
        ).count()
        
        if total_orders > 0:
            delivery_rate = (confirmed_orders / total_orders) * 100
            seller_rating.delivery_rate = Decimal(str(delivery_rate)).quantize(Decimal('0.01'))
        else:
            seller_rating.delivery_rate = Decimal('0.00')
        
        seller_rating.total_sales = confirmed_orders
        seller_rating.save()
        
        return seller_rating
    
    @staticmethod
    def get_seller_reviews(seller: User, limit: Optional[int] = None):
        """
        Get reviews for a seller.
        
        Args:
            seller: Seller to get reviews for
            limit: Optional limit on number of reviews
            
        Returns:
            QuerySet of Review objects
        """
        reviews = Review.objects.filter(
            seller=seller
        ).select_related('buyer', 'order').order_by('-created_at')
        
        if limit:
            reviews = reviews[:limit]
        
        return reviews
    
    @staticmethod
    def get_seller_rating(seller: User) -> Optional[SellerRating]:
        """
        Get seller's rating statistics.
        
        Args:
            seller: Seller to get rating for
            
        Returns:
            SellerRating or None
        """
        try:
            return SellerRating.objects.get(seller=seller)
        except SellerRating.DoesNotExist:
            return None
