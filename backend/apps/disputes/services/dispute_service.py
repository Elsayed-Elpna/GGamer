"""
Dispute service - main business logic for dispute management.
Handles dispute creation, evidence, messaging, and admin decisions.
"""
from typing import Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from apps.disputes.models import (
    Dispute, DisputeEvidence, DisputeMessage, DisputeDecision
)
from apps.orders.models import Order
from apps.orders.services.state_machine import StateMachine
from apps.orders.services.escrow_service import EscrowService
from apps.accounts.models import User


class DisputeService:
    """
    Service for managing disputes.
    Handles creation, evidence, messaging, and admin decisions.
    """
    
    @staticmethod
    @transaction.atomic
    def create_dispute(
        order: Order,
        user: User,
        reason: str,
        description: str,
        ip_address: Optional[str] = None
    ) -> Dispute:
        """
        Create a new dispute for an order.
        
        Security:
        - Only order participants can create disputes
        - Order must be in valid state
        - Transitions order to DISPUTED state
        
        Args:
            order: Order to dispute
            user: User creating dispute
            reason: Short reason
            description: Detailed description
            ip_address: User IP
            
        Returns:
            Created Dispute
        """
        # Validate user is participant
        if not order.is_participant(user):
            raise PermissionDenied("Only order participants can create disputes")
        
        # Check if dispute already exists
        if order.disputes.filter(status__in=[Dispute.OPEN, Dispute.IN_REVIEW]).exists():
            raise ValidationError("An active dispute already exists for this order")
        
        # Determine who is creating
        if order.is_buyer(user):
            created_by_role = Dispute.BUYER
        else:
            created_by_role = Dispute.SELLER
        
        # Create dispute
        dispute = Dispute.objects.create(
            order=order,
            created_by_user=user,
            created_by_role=created_by_role,
            reason=reason[:100],
            description=description[:2000],
            status=Dispute.OPEN
        )
        
        # Transition order to DISPUTED state
        StateMachine.transition(
            order=order,
            to_state=Order.DISPUTED,
            user=user,
            reason=f"Dispute created: {reason}",
            ip_address=ip_address
        )
        
        return dispute
    
    @staticmethod
    @transaction.atomic
    def upload_evidence(
        dispute: Dispute,
        user: User,
        file,
        description: str = ""
    ) -> DisputeEvidence:
        """
        Upload evidence for a dispute.
        
        Security:
        - Only participants and staff can upload
        - File validation
        
        Args:
            dispute: Dispute to add evidence to
            user: User uploading
            file: File to upload
            description: Evidence description
            
        Returns:
            Created DisputeEvidence
        """
        # Validate user can upload
        order = dispute.order
        if not (order.is_participant(user) or user.is_staff):
            raise PermissionDenied("You cannot upload evidence to this dispute")
        
        # Validate dispute is not closed
        if dispute.status == Dispute.CLOSED:
            raise ValidationError("Cannot upload evidence to closed dispute")
        
        # Create evidence
        evidence = DisputeEvidence.objects.create(
            dispute=dispute,
            uploaded_by=user,
            file=file,
            file_type=file.content_type,
            file_size=file.size,
            description=description[:500]
        )
        
        return evidence
    
    @staticmethod
    @transaction.atomic
    def send_message(
        dispute: Dispute,
        user: User,
        message: str,
        is_internal: bool = False
    ) -> DisputeMessage:
        """
        Send message in dispute.
        
        Security:
        - Participants can send regular messages
        - Only staff can send internal messages
        
        Args:
            dispute: Dispute
            user: User sending message
            message: Message content
            is_internal: Whether message is admin-only
            
        Returns:
            Created DisputeMessage
        """
        # Validate user can send
        order = dispute.order
        if not (order.is_participant(user) or user.is_staff):
            raise PermissionDenied("You cannot send messages in this dispute")
        
        # Only staff can send internal messages
        if is_internal and not user.is_staff:
            raise PermissionDenied("Only staff can send internal messages")
        
        # Create message
        dispute_message = DisputeMessage.objects.create(
            dispute=dispute,
            sender=user,
            message=message[:2000],
            is_internal=is_internal
        )
        
        return dispute_message
    
    @staticmethod
    @transaction.atomic
    def refund_buyer_full(
        dispute: Dispute,
        admin: User,
        reason: str,
        ip_address: Optional[str] = None
    ) -> DisputeDecision:
        """
        Admin decision: Full refund to buyer.
        
        Args:
            dispute: Dispute to resolve
            admin: Admin making decision
            reason: Reason for decision
            ip_address: Admin IP
            
        Returns:
            Created DisputeDecision
        """
        if not admin.is_staff:
            raise PermissionDenied("Only staff can make decisions")
        
        order = dispute.order
        
        # Refund via escrow
        if hasattr(order, 'escrow'):
            EscrowService.refund_buyer(order.escrow)
        
        # Create decision
        decision = DisputeDecision.objects.create(
            dispute=dispute,
            admin=admin,
            decision_type=DisputeDecision.REFUND_BUYER,
            reason=reason,
            ip_address=ip_address
        )
        
        # Update dispute status
        dispute.status = Dispute.RESOLVED
        dispute.resolved_at = timezone.now()
        dispute.save()
        
        # Transition order to REFUNDED
        StateMachine.transition(
            order=order,
            to_state=Order.REFUNDED,
            user=admin,
            reason=f"Admin decision: {reason}",
            ip_address=ip_address
        )
        
        return decision
    
    @staticmethod
    @transaction.atomic
    def release_to_seller(
        dispute: Dispute,
        admin: User,
        reason: str,
        ip_address: Optional[str] = None
    ) -> DisputeDecision:
        """
        Admin decision: Release funds to seller.
        
        Args:
            dispute: Dispute to resolve
            admin: Admin making decision
            reason: Reason for decision
            ip_address: Admin IP
            
        Returns:
            Created DisputeDecision
        """
        if not admin.is_staff:
            raise PermissionDenied("Only staff can make decisions")
        
        order = dispute.order
        
        # Release via escrow
        if hasattr(order, 'escrow'):
            EscrowService.release_funds(order.escrow)
        
        # Create decision
        decision = DisputeDecision.objects.create(
            dispute=dispute,
            admin=admin,
            decision_type=DisputeDecision.RELEASE_SELLER,
            reason=reason,
            ip_address=ip_address
        )
        
        # Update dispute status
        dispute.status = Dispute.RESOLVED
        dispute.resolved_at = timezone.now()
        dispute.save()
        
        # Transition order to CONFIRMED
        StateMachine.transition(
            order=order,
            to_state=Order.CONFIRMED,
            user=admin,
            reason=f"Admin decision: {reason}",
            ip_address=ip_address
        )
        
        return decision
    
    @staticmethod
    @transaction.atomic
    def partial_refund(
        dispute: Dispute,
        admin: User,
        buyer_amount: Decimal,
        seller_amount: Decimal,
        reason: str,
        ip_address: Optional[str] = None
    ) -> DisputeDecision:
        """
        Admin decision: Partial refund (split funds).
        
        Args:
            dispute: Dispute to resolve
            admin: Admin making decision
            buyer_amount: Amount to refund to buyer
            seller_amount: Amount to release to seller
            reason: Reason for decision
            ip_address: Admin IP
            
        Returns:
            Created DisputeDecision
        """
        if not admin.is_staff:
            raise PermissionDenied("Only staff can make decisions")
        
        order = dispute.order
        
        # Partial refund via escrow
        if hasattr(order, 'escrow'):
            EscrowService.partial_refund(
                order.escrow,
                buyer_amount=buyer_amount,
                seller_amount=seller_amount
            )
        
        # Create decision
        decision = DisputeDecision.objects.create(
            dispute=dispute,
            admin=admin,
            decision_type=DisputeDecision.PARTIAL_REFUND,
            buyer_refund_amount=buyer_amount,
            seller_release_amount=seller_amount,
            reason=reason,
            ip_address=ip_address
        )
        
        # Update dispute status
        dispute.status = Dispute.RESOLVED
        dispute.resolved_at = timezone.now()
        dispute.save()
        
        # Transition order to REFUNDED (partial)
        StateMachine.transition(
            order=order,
            to_state=Order.REFUNDED,
            user=admin,
            reason=f"Admin decision (partial): {reason}",
            ip_address=ip_address
        )
        
        return decision
    
    @staticmethod
    @transaction.atomic
    def ban_seller(
        dispute: Dispute,
        admin: User,
        reason: str,
        ip_address: Optional[str] = None
    ) -> DisputeDecision:
        """
        Admin decision: Ban seller and refund buyer.
        
        Args:
            dispute: Dispute
            admin: Admin making decision
            reason: Reason for ban
            ip_address: Admin IP
            
        Returns:
            Created DisputeDecision
        """
        if not admin.is_staff:
            raise PermissionDenied("Only staff can make decisions")
        
        order = dispute.order
        seller = order.seller
        
        # Ban seller
        seller.is_active = False
        seller.save()
        
        # Refund buyer
        if hasattr(order, 'escrow'):
            EscrowService.refund_buyer(order.escrow)
        
        # Create decision
        decision = DisputeDecision.objects.create(
            dispute=dispute,
            admin=admin,
            decision_type=DisputeDecision.BAN_SELLER,
            reason=reason,
            ip_address=ip_address
        )
        
        # Update dispute status
        dispute.status = Dispute.RESOLVED
        dispute.resolved_at = timezone.now()
        dispute.save()
        
        # Transition order
        StateMachine.transition(
            order=order,
            to_state=Order.REFUNDED,
            user=admin,
            reason=f"Seller banned: {reason}",
            ip_address=ip_address
        )
        
        return decision
    
    @staticmethod
    @transaction.atomic
    def close_dispute(
        dispute: Dispute,
        admin: User,
        reason: str,
        ip_address: Optional[str] = None
    ) -> DisputeDecision:
        """
        Admin decision: Close dispute with no action.
        
        Args:
            dispute: Dispute
            admin: Admin making decision
            reason: Reason for closing
            ip_address: Admin IP
            
        Returns:
            Created DisputeDecision
        """
        if not admin.is_staff:
            raise PermissionDenied("Only staff can make decisions")
        
        # Create decision
        decision = DisputeDecision.objects.create(
            dispute=dispute,
            admin=admin,
            decision_type=DisputeDecision.CLOSE_NO_ACTION,
            reason=reason,
            ip_address=ip_address
        )
        
        # Update dispute status
        dispute.status = Dispute.CLOSED
        dispute.save()
        
        return decision
