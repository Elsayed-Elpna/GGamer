"""
Reviews models - Buyer ratings for sellers.
Production-ready with automatic rating calculation and fake review prevention.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.accounts.models import User
from apps.orders.models import Order


class Review(models.Model):
    """
    Buyer review for a seller after order completion.
    One review per order.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='review'
    )
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_given'
    )
    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_received'
    )
    
    # Rating (1-5 stars)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    
    # Review content
    comment = models.TextField(
        max_length=1000,
        blank=True,
        help_text="Optional review comment"
    )
    
    # Delivery metrics
    delivery_speed = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Speed of delivery (1-5)"
    )
    communication = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Communication quality (1-5)"
    )
    as_described = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Item as described (1-5)"
    )
    
    # Fake review detection
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address for fake review detection"
    )
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        indexes = [
            models.Index(fields=['seller', '-created_at']),
            models.Index(fields=['buyer', '-created_at']),
            models.Index(fields=['rating', '-created_at']),
        ]
    
    def __str__(self):
        return f"Review by {self.buyer.email} for {self.seller.email} - {self.rating}★"
    
    def average_rating(self):
        """Calculate average of all rating components."""
        return (self.rating + self.delivery_speed + self.communication + self.as_described) / 4


class SellerRating(models.Model):
    """
    Aggregated seller rating statistics.
    Auto-updated when reviews are created.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='seller_rating'
    )
    
    # Aggregate statistics
    total_reviews = models.IntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Average rating (1-5)"
    )
    
    # Individual metrics
    average_delivery_speed = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00
    )
    average_communication = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00
    )
    average_as_described = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00
    )
    
    # Rating breakdown (count of each star)
    five_star_count = models.IntegerField(default=0)
    four_star_count = models.IntegerField(default=0)
    three_star_count = models.IntegerField(default=0)
    two_star_count = models.IntegerField(default=0)
    one_star_count = models.IntegerField(default=0)
    
    # Performance metrics
    total_sales = models.IntegerField(
        default=0,
        help_text="Total completed orders"
    )
    delivery_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Percentage of orders completed (0-100)"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Seller Rating'
        verbose_name_plural = 'Seller Ratings'
    
    def __str__(self):
        return f"{self.seller.email} - {self.average_rating}★ ({self.total_reviews} reviews)"
    
    def delivery_percentage(self):
        """Get delivery rate as percentage."""
        return float(self.delivery_rate)
