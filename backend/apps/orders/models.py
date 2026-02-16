"""
Orders models - Order state machine, Escrow, Proof uploads.
Production-ready with full audit trails and security.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, FileExtensionValidator
from django.utils import timezone
from apps.accounts.models import User


class Order(models.Model):
    """
    Core order model with state machine.
    Handles buyer-seller transactions with escrow.
    """
    # Order states
    CREATED = 'CREATED'
    PAID = 'PAID'
    IN_PROGRESS = 'IN_PROGRESS'
    DELIVERED = 'DELIVERED'
    CONFIRMED = 'CONFIRMED'
    DISPUTED = 'DISPUTED'
    REFUNDED = 'REFUNDED'
    CANCELLED = 'CANCELLED'
    
    STATE_CHOICES = [
        (CREATED, 'Created'),
        (PAID, 'Paid'),
        (IN_PROGRESS, 'In Progress'),
        (DELIVERED, 'Delivered'),
        (CONFIRMED, 'Confirmed'),
        (DISPUTED, 'Disputed'),
        (REFUNDED, 'Refunded'),
        (CANCELLED, 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relations
    buyer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # Don't delete users with orders
        related_name='purchases'
    )
    seller = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='sales'
    )
    offer = models.ForeignKey(
        'marketplace.Offer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    
    # Order details
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(1000)]  # SECURITY: Prevent huge orders
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price per unit at time of order"
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total amount paid by buyer"
    )
    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Platform commission"
    )
    seller_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount seller receives after platform fee"
    )
    
    # Delivery info
    delivery_method = models.CharField(max_length=50)
    buyer_notes = models.TextField(
        blank=True,
        max_length=1000,
        help_text="Buyer notes/instructions"
    )
    seller_notes = models.TextField(
        blank=True,
        max_length=1000,
        help_text="Seller internal notes"
    )
    
    # State
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default=CREATED,
        db_index=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        indexes = [
            models.Index(fields=['buyer', 'state', '-created_at']),
            models.Index(fields=['seller', 'state', '-created_at']),
            models.Index(fields=['state', '-created_at']),
        ]
    
    def __str__(self):
        return f"Order {self.id} - {self.state}"
    
    def is_buyer(self, user):
        """Check if user is the buyer."""
        return self.buyer == user
    
    def is_seller(self, user):
        """Check if user is the seller."""
        return self.seller == user
    
    def is_participant(self, user):
        """Check if user is buyer or seller."""
        return self.is_buyer(user) or self.is_seller(user)


class OrderStateLog(models.Model):
    """
    Audit trail for order state transitions.
    Logs every state change with reason and IP.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='state_logs'
    )
    from_state = models.CharField(max_length=20)
    to_state = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who triggered change (null for system)"
    )
    reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order State Log'
        verbose_name_plural = 'Order State Logs'
        indexes = [
            models.Index(fields=['order', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.order.id}: {self.from_state} → {self.to_state}"


class EscrowAccount(models.Model):
    """
    Escrow account holding funds for an order.
    Funds are held until buyer confirms or dispute resolves.
    """
    # Escrow status
    HOLDING = 'HOLDING'
    RELEASED = 'RELEASED'
    REFUNDED = 'REFUNDED'
    PARTIAL = 'PARTIAL'
    
    STATUS_CHOICES = [
        (HOLDING, 'Holding Funds'),
        (RELEASED, 'Released to Seller'),
        (REFUNDED, 'Refunded to Buyer'),
        (PARTIAL, 'Partial Refund'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
        related_name='escrow'
    )
    
    # Amounts
    amount_held = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total amount held in escrow"
    )
    amount_released = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount released to seller"
    )
    amount_refunded = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount refunded to buyer"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=HOLDING,
        db_index=True
    )
    
    # Timestamps
    held_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Escrow Account'
        verbose_name_plural = 'Escrow Accounts'
    
    def __str__(self):
        return f"Escrow for Order {self.order.id} - {self.status}"
    
    def remaining_balance(self):
        """Calculate remaining balance in escrow."""
        return self.amount_held - self.amount_released - self.amount_refunded


class ProofUpload(models.Model):
    """
    Delivery proof uploaded by seller.
    Can be images, videos, or screenshots.
    """
    # File types
    IMAGE = 'IMAGE'
    VIDEO = 'VIDEO'
    SCREENSHOT = 'SCREENSHOT'
    
    FILE_TYPE_CHOICES = [
        (IMAGE, 'Image'),
        (VIDEO, 'Video'),
        (SCREENSHOT, 'Screenshot'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='proofs'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    file = models.FileField(
        upload_to='order_proofs/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'mp4', 'webm']
            )
        ]
    )
    description = models.TextField(
        max_length=500,
        blank=True,
        help_text="Description of proof"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Proof Upload'
        verbose_name_plural = 'Proof Uploads'
    
    def __str__(self):
        return f"Proof for Order {self.order.id} - {self.file_type}"
