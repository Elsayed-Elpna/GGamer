"""
Disputes models - Ticket system for order disputes.
Production-ready with evidence, internal chat, and admin decisions.
"""
import uuid
from django.db import models
from django.core.validators import FileExtensionValidator
from apps.accounts.models import User
from apps.orders.models import Order


class Dispute(models.Model):
    """
    Dispute ticket linked to an order.
    Created by buyer or seller when there's an issue.
    """
    # Dispute status
    OPEN = 'OPEN'
    IN_REVIEW = 'IN_REVIEW'
    RESOLVED = 'RESOLVED'
    CLOSED = 'CLOSED'
    
    STATUS_CHOICES = [
        (OPEN, 'Open'),
        (IN_REVIEW, 'In Review'),
        (RESOLVED, 'Resolved'),
        (CLOSED, 'Closed'),
    ]
    
    # Who created dispute
    BUYER = 'BUYER'
    SELLER = 'SELLER'
    
    CREATED_BY_CHOICES = [
        (BUYER, 'Buyer'),
        (SELLER, 'Seller'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='disputes'
    )
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='disputes_created'
    )
    created_by_role = models.CharField(
        max_length=20,
        choices=CREATED_BY_CHOICES,
        help_text="Who created the dispute"
    )
    
    # Dispute details
    reason = models.CharField(
        max_length=100,
        help_text="Short reason for dispute"
    )
    description = models.TextField(
        max_length=2000,
        help_text="Detailed description of issue"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=OPEN,
        db_index=True
    )
    
    # Admin assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_disputes',
        help_text="Admin/support assigned to this dispute"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Dispute'
        verbose_name_plural = 'Disputes'
        indexes = [
            models.Index(fields=['order', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['assigned_to', '-created_at']),
        ]
    
    def __str__(self):
        return f"Dispute {self.id} - {self.order.id}"


class DisputeEvidence(models.Model):
    """
    Evidence uploaded for a dispute.
    Can be uploaded by buyer, seller, or admin.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(
        Dispute,
        on_delete=models.CASCADE,
        related_name='evidence'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    file = models.FileField(
        upload_to='dispute_evidence/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'pdf', 'txt', 'mp4']
            )
        ]
    )
    file_type = models.CharField(max_length=50)
    file_size = models.IntegerField(help_text="File size in bytes")
    description = models.TextField(
        max_length=500,
        blank=True,
        help_text="Description of evidence"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Dispute Evidence'
        verbose_name_plural = 'Dispute Evidence'
    
    def __str__(self):
        return f"Evidence for Dispute {self.dispute.id}"


class DisputeMessage(models.Model):
    """
    Internal chat messages for dispute.
    Between buyer, seller, and admin.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(
        Dispute,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    message = models.TextField(max_length=2000)
    is_internal = models.BooleanField(
        default=False,
        help_text="True for admin-only internal notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Dispute Message'
        verbose_name_plural = 'Dispute Messages'
        indexes = [
            models.Index(fields=['dispute', 'created_at']),
        ]
    
    def __str__(self):
        return f"Message in Dispute {self.dispute.id}"


class DisputeDecision(models.Model):
    """
    Admin decision on a dispute.
    Logs all admin actions with full audit trail.
    """
    # Decision types
    REFUND_BUYER = 'REFUND_BUYER'
    RELEASE_SELLER = 'RELEASE_SELLER'
    PARTIAL_REFUND = 'PARTIAL_REFUND'
    BAN_SELLER = 'BAN_SELLER'
    CLOSE_NO_ACTION = 'CLOSE_NO_ACTION'
    
    DECISION_CHOICES = [
        (REFUND_BUYER, 'Refund Buyer (Full)'),
        (RELEASE_SELLER, 'Release to Seller'),
        (PARTIAL_REFUND, 'Partial Refund'),
        (BAN_SELLER, 'Ban Seller'),
        (CLOSE_NO_ACTION, 'Close (No Action)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(
        Dispute,
        on_delete=models.CASCADE,
        related_name='decisions'
    )
    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="Admin who made the decision"
    )
    decision_type = models.CharField(max_length=20, choices=DECISION_CHOICES)
    
    # For partial refunds
    buyer_refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount refunded to buyer"
    )
    seller_release_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount released to seller"
    )
    
    reason = models.TextField(
        max_length=1000,
        help_text="Admin's reason for decision"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Dispute Decision'
        verbose_name_plural = 'Dispute Decisions'
        indexes = [
            models.Index(fields=['dispute', '-created_at']),
            models.Index(fields=['admin', '-created_at']),
        ]
    
    def __str__(self):
        return f"Decision for Dispute {self.dispute.id} - {self.decision_type}"
