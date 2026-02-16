"""
Order state machine service.
Handles ALL state transitions with validation and security.
Production-ready with race condition prevention.
"""
from typing import Optional
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from apps.orders.models import Order, OrderStateLog
from apps.accounts.models import User


class StateMachine:
    """
    Order state machine with strict transition rules.
    Prevents invalid state changes and race conditions.
    """
    
    # Valid state transitions
    TRANSITIONS = {
        Order.CREATED: [Order.PAID, Order.CANCELLED],
        Order.PAID: [Order.IN_PROGRESS, Order.DISPUTED, Order.CANCELLED],
        Order.IN_PROGRESS: [Order.DELIVERED, Order.DISPUTED, Order.CANCELLED],
        Order.DELIVERED: [Order.CONFIRMED, Order.DISPUTED],
        Order.DISPUTED: [Order.REFUNDED, Order.CONFIRMED, Order.CANCELLED],
        Order.CONFIRMED: [],  # Terminal state
        Order.REFUNDED: [],   # Terminal state
        Order.CANCELLED: [],  # Terminal state
    }
    
    @classmethod
    def can_transition(cls, from_state: str, to_state: str) -> bool:
        """Check if transition is valid."""
        return to_state in cls.TRANSITIONS.get(from_state, [])
    
    @classmethod
    @transaction.atomic
    def transition(
        cls,
        order: Order,
        to_state: str,
        user: Optional[User] = None,
        reason: str = "",
        ip_address: Optional[str] = None
    ) -> Order:
        """
        Transition order to new state with validation.
        
        Security:
        - Validates state transition
        - Uses select_for_update to prevent race conditions
        - Logs all transitions with audit trail
        
        Args:
            order: Order instance
            to_state: Target state
            user: User making the change (None for system)
            reason: Reason for transition
            ip_address: IP address of requester
            
        Returns:
            Updated order
            
        Raises:
            ValidationError: If transition is invalid
        """
        # Lock the row to prevent race conditions
        locked_order = Order.objects.select_for_update().get(id=order.id)
        
        # Validate transition
        if not cls.can_transition(locked_order.state, to_state):
            raise ValidationError(
                f"Cannot transition from {locked_order.state} to {to_state}"
            )
        
        # Store old state
        old_state = locked_order.state
        
        # Update state
        locked_order.state = to_state
        
        # Set timestamps for specific states
        if to_state == Order.PAID:
            locked_order.paid_at = timezone.now()
        elif to_state in [Order.CONFIRMED, Order.REFUNDED, Order.CANCELLED]:
            locked_order.completed_at = timezone.now()
        
        locked_order.save()
        
        # Log state change
        OrderStateLog.objects.create(
            order=locked_order,
            from_state=old_state,
            to_state=to_state,
            changed_by=user,
            reason=reason,
            ip_address=ip_address
        )
        
        return locked_order
    
    @classmethod
    def validate_user_can_transition(
        cls,
        order: Order,
        user: User,
        to_state: str
    ) -> None:
        """
        Validate that user has permission to make this state transition.
        
        Raises:
            PermissionDenied: If user cannot make this transition
        """
        # Map states to allowed roles
        state_permissions = {
            Order.PAID: ['system'],  # Only payment webhook can mark as paid
            Order.IN_PROGRESS: ['seller'],  # Only seller can start work
            Order.DELIVERED: ['seller'],  # Only seller can mark delivered
            Order.CONFIRMED: ['buyer'],  # Only buyer can confirm
            Order.DISPUTED: ['buyer', 'seller'],  # Either can dispute
            Order.CANCELLED: ['buyer', 'seller', 'admin'],
            Order.REFUNDED: ['admin'],  # Only admin can refund
        }
        
        allowed_roles = state_permissions.get(to_state, [])
        
        # Check permissions
        if 'seller' in allowed_roles and order.is_seller(user):
            return
        if 'buyer' in allowed_roles and order.is_buyer(user):
            return
        if 'admin' in allowed_roles and user.is_staff:
            return
        if 'system' in allowed_roles:
            # System transitions handled separately
            raise PermissionDenied("This transition requires system access")
        
        raise PermissionDenied(
            f"You do not have permission to transition order to {to_state}"
        )
