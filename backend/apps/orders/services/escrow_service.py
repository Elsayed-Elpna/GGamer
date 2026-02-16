"""
Escrow service - manages fund holding and release.
Critical security: handles real money transactions.
"""
from decimal import Decimal
from typing import Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.orders.models import Order, EscrowAccount


class EscrowService:
    """
    Manages escrow accounts for orders.
    Holds funds until buyer confirms or dispute resolves.
    """
    
    @staticmethod
    @transaction.atomic
    def create_escrow(order: Order) -> EscrowAccount:
        """
        Create escrow account for paid order.
        Called after payment webhook confirms payment.
        
        Args:
            order: Order that was just paid
            
        Returns:
            Created escrow account
        """
        # Validate order state
        if order.state != Order.PAID:
            raise ValidationError("Can only create escrow for PAID orders")
        
        # Check if escrow already exists
        if hasattr(order, 'escrow'):
            raise ValidationError("Escrow already exists for this order")
        
        # Create escrow
        escrow = EscrowAccount.objects.create(
            order=order,
            amount_held=order.total_amount,
            status=EscrowAccount.HOLDING
        )
        
        return escrow
    
    @staticmethod
    @transaction.atomic
    def release_funds(
        escrow: EscrowAccount,
        amount: Optional[Decimal] = None
    ) -> EscrowAccount:
        """
        Release funds from escrow to seller.
        Called when buyer confirms delivery.
        
        Args:
            escrow: Escrow account
            amount: Amount to release (default: all remaining)
            
        Returns:
            Updated escrow account
        """
        # Default to full remaining balance
        if amount is None:
            amount = escrow.remaining_balance()
        
        # Validate amount
        if amount <= 0:
            raise ValidationError("Release amount must be positive")
        
        if amount > escrow.remaining_balance():
            raise ValidationError("Cannot release more than remaining balance")
        
        # Lock row
        locked_escrow = EscrowAccount.objects.select_for_update().get(
            id=escrow.id
        )
        
        # Update amounts
        locked_escrow.amount_released += amount
        
        # Update status
        remaining = locked_escrow.remaining_balance()
        if remaining == 0:
            locked_escrow.status = EscrowAccount.RELEASED
            locked_escrow.released_at = timezone.now()
        else:
            locked_escrow.status = EscrowAccount.PARTIAL
        
        locked_escrow.save()
        
        # TODO: Trigger actual money transfer to seller
        # This would integrate with payment gateway's payout API
        
        return locked_escrow
    
    @staticmethod
    @transaction.atomic
    def refund_buyer(
        escrow: EscrowAccount,
        amount: Optional[Decimal] = None
    ) -> EscrowAccount:
        """
        Refund funds from escrow to buyer.
        Called when order is cancelled or dispute resolved in buyer's favor.
        
        Args:
            escrow: Escrow account
            amount: Amount to refund (default: all remaining)
            
        Returns:
            Updated escrow account
        """
        # Default to full remaining balance
        if amount is None:
            amount = escrow.remaining_balance()
        
        # Validate amount
        if amount <= 0:
            raise ValidationError("Refund amount must be positive")
        
        if amount > escrow.remaining_balance():
            raise ValidationError("Cannot refund more than remaining balance")
        
        # Lock row
        locked_escrow = EscrowAccount.objects.select_for_update().get(
            id=escrow.id
        )
        
        # Update amounts
        locked_escrow.amount_refunded += amount
        
        # Update status
        remaining = locked_escrow.remaining_balance()
        if remaining == 0:
            locked_escrow.status = EscrowAccount.REFUNDED
        else:
            locked_escrow.status = EscrowAccount.PARTIAL
        
        locked_escrow.save()
        
        # TODO: Trigger actual refund via payment gateway
        # This would call Paymob's refund API
        
        return locked_escrow
    
    @staticmethod
    @transaction.atomic
    def partial_refund(
        escrow: EscrowAccount,
        buyer_amount: Decimal,
        seller_amount: Decimal
    ) -> EscrowAccount:
        """
        Partial refund for dispute resolution.
        Splits remaining funds between buyer and seller.
        
        Args:
            escrow: Escrow account
            buyer_amount: Amount to refund to buyer
            seller_amount: Amount to release to seller
            
        Returns:
            Updated escrow account
        """
        total = buyer_amount + seller_amount
        remaining = escrow.remaining_balance()
        
        # Validate amounts
        if buyer_amount < 0 or seller_amount < 0:
            raise ValidationError("Amounts must be non-negative")
        
        if total > remaining:
            raise ValidationError(
                f"Total ({total}) exceeds remaining balance ({remaining})"
            )
        
        # Lock row
        locked_escrow = EscrowAccount.objects.select_for_update().get(
            id=escrow.id
        )
        
        # Update amounts
        locked_escrow.amount_refunded += buyer_amount
        locked_escrow.amount_released += seller_amount
        locked_escrow.status = EscrowAccount.PARTIAL
        
        locked_escrow.save()
        
        # TODO: Trigger refund and payout
        
        return locked_escrow
