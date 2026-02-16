"""
Order service - main business logic for order management.
Orchestrates state machine, escrow, and validations.
"""
from decimal import Decimal
from typing import Optional
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from apps.orders.models import Order, ProofUpload
from apps.orders.services.state_machine import StateMachine
from apps.orders.services.escrow_service import EscrowService
from apps.marketplace.models import Offer
from apps.marketplace.services.offer_service import OfferService
from apps.accounts.models import User


class OrderService:
    """
    Main service for order operations.
    Coordinates state machine, escrow, and offer stock.
    """
    
    # Platform fee percentage (e.g., 10%)
    PLATFORM_FEE_PERCENT = Decimal('10.00')
    
    @classmethod
    def calculate_platform_fee(cls, total_amount: Decimal) -> Decimal:
        """Calculate platform fee from total amount."""
        return (total_amount * cls.PLATFORM_FEE_PERCENT / 100).quantize(
            Decimal('0.01')
        )
    
    @classmethod
    @transaction.atomic
    def create_order(
        cls,
        buyer: User,
        offer: Offer,
        quantity: int,
        buyer_notes: str = ""
    ) -> Order:
        """
        Create a new order.
        
        Security:
        - Validates offer availability
        - Prevents self-purchase
        - Decrements stock with race condition protection
        
        Args:
            buyer: User creating the order
            offer: Offer being purchased
            quantity: Quantity to purchase
            buyer_notes: Optional buyer notes
            
        Returns:
            Created order in CREATED state
        """
        # Prevent self-purchase
        if buyer == offer.seller:
            raise ValidationError("Cannot purchase your own offer")
        
        # Validate offer status
        if offer.status != Offer.ACTIVE:
            raise ValidationError("This offer is not available")
        
        # Validate quantity
        if not offer.can_purchase(quantity):
            raise ValidationError(
                f"Invalid quantity. Min: {offer.min_purchase}, "
                f"Available: {offer.available_stock}"
            )
        
        # Calculate amounts
        unit_price = offer.price_per_unit
        total_amount = offer.calculate_total_price(quantity)
        platform_fee = cls.calculate_platform_fee(total_amount)
        seller_amount = total_amount - platform_fee
        
        # Create order
        order = Order.objects.create(
            buyer=buyer,
            seller=offer.seller,
            offer=offer,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            platform_fee=platform_fee,
            seller_amount=seller_amount,
            delivery_method=offer.delivery_method,
            buyer_notes=buyer_notes[:1000],
            state=Order.CREATED
        )
        
        # Decrement offer stock (race-safe)
        OfferService.decrement_stock(offer, quantity)
        
        return order
    
    @classmethod
    @transaction.atomic
    def mark_as_paid(
        cls,
        order: Order,
        ip_address: Optional[str] = None
    ) -> Order:
        """
        Mark order as paid (called by payment webhook).
        Creates escrow account to hold funds.
        
        Args:
            order: Order to mark as paid
            ip_address: IP address (for audit)
            
        Returns:
            Updated order
        """
        # Transition to PAID
        order = StateMachine.transition(
            order=order,
            to_state=Order.PAID,
            user=None,  # System action
            reason="Payment confirmed by payment gateway",
            ip_address=ip_address
        )
        
        # Create escrow account
        EscrowService.create_escrow(order)
        
        return order
    
    @classmethod
    @transaction.atomic
    def start_order(
        cls,
        order: Order,
        seller: User,
        ip_address: Optional[str] = None
    ) -> Order:
        """
        Seller starts working on order.
        
        Args:
            order: Order to start
            seller: Seller starting work
            ip_address: IP address
            
        Returns:
            Updated order
        """
        # Validate seller
        if not order.is_seller(seller):
            raise PermissionDenied("Only the seller can start this order")
        
        # Validate state
        StateMachine.validate_user_can_transition(
            order, seller, Order.IN_PROGRESS
        )
        
        # Transition
        order = StateMachine.transition(
            order=order,
            to_state=Order.IN_PROGRESS,
            user=seller,
            reason="Seller started working on order",
            ip_address=ip_address
        )
        
        return order
    
    @classmethod
    @transaction.atomic
    def deliver_order(
        cls,
        order: Order,
        seller: User,
        proof_files: list,
        description: str = "",
        ip_address: Optional[str] = None
    ) -> Order:
        """
        Seller delivers order with proof.
        
        Args:
            order: Order to deliver
            seller: Seller delivering
            proof_files: List of proof files (images/videos)
            description: Delivery description
            ip_address: IP address
            
        Returns:
            Updated order
        """
        # Validate seller
        if not order.is_seller(seller):
            raise PermissionDenied("Only the seller can deliver this order")
        
        # Validate state
        StateMachine.validate_user_can_transition(
            order, seller, Order.DELIVERED
        )
        
        # Upload proofs
        for file in proof_files:
            # Determine file type
            file_extension = file.name.split('.')[-1].lower()
            if file_extension in ['jpg', 'jpeg', 'png', 'gif']:
                file_type = ProofUpload.IMAGE
            elif file_extension in ['mp4', 'webm']:
                file_type = ProofUpload.VIDEO
            else:
                file_type = ProofUpload.SCREENSHOT
            
            ProofUpload.objects.create(
                order=order,
                uploaded_by=seller,
                file_type=file_type,
                file=file,
                description=description
            )
        
        # Transition
        order = StateMachine.transition(
            order=order,
            to_state=Order.DELIVERED,
            user=seller,
            reason="Seller uploaded delivery proof",
            ip_address=ip_address
        )
        
        return order
    
    @classmethod
    @transaction.atomic
    def confirm_delivery(
        cls,
        order: Order,
        buyer: User,
        ip_address: Optional[str] = None
    ) -> Order:
        """
        Buyer confirms receipt of order.
        Releases escrow funds to seller.
        
        Args:
            order: Order to confirm
            buyer: Buyer confirming
            ip_address: IP address
            
        Returns:
            Updated order
        """
        # Validate buyer
        if not order.is_buyer(buyer):
            raise PermissionDenied("Only the buyer can confirm this order")
        
        # Validate state
        StateMachine.validate_user_can_transition(
            order, buyer, Order.CONFIRMED
        )
        
        # Transition
        order = StateMachine.transition(
            order=order,
            to_state=Order.CONFIRMED,
            user=buyer,
            reason="Buyer confirmed delivery",
            ip_address=ip_address
        )
        
        # Release escrow funds to seller
        if hasattr(order, 'escrow'):
            EscrowService.release_funds(order.escrow)
        
        return order
    
    @classmethod
    @transaction.atomic  
    def cancel_order(
        cls,
        order: Order,
        user: User,
        reason: str,
        ip_address: Optional[str] = None
    ) -> Order:
        """
        Cancel order.
        Refunds buyer if order was paid.
        
        Args:
            order: Order to cancel
            user: User cancelling
            reason: Cancellation reason
            ip_address: IP address
            
        Returns:
            Updated order
        """
        # Validate user can cancel
        if not (order.is_participant(user) or user.is_staff):
            raise PermissionDenied("You cannot cancel this order")
        
        # Validate state
        StateMachine.validate_user_can_transition(
            order, user, Order.CANCELLED
        )
        
        # Transition
        order = StateMachine.transition(
            order=order,
            to_state=Order.CANCELLED,
            user=user,
            reason=reason,
            ip_address=ip_address
        )
        
        # Refund if paid
        if hasattr(order, 'escrow') and order.escrow.remaining_balance() > 0:
            EscrowService.refund_buyer(order.escrow)
        
        return order
