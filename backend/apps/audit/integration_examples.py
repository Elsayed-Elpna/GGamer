"""
Example integrations for audit logging throughout the system.
These examples show how to use the audit system in different apps.
"""

# =====================================================
# Example 1: Authentication Logging
# =====================================================

# In apps/accounts/views.py or authentication views:

from apps.audit.logging_utils import audit_logger
from apps.audit.models import AuthenticationLog

def login_view(request):
    """Example login with audit logging."""
    email = request.data.get('email')
    password = request.data.get('password')
    
    try:
        # Authenticate user
        user = authenticate(email=email, password=password)
        
        if user:
            # Log successful login
            audit_logger.log_authentication(
                email=email,
                event_type=AuthenticationLog.LOGIN_SUCCESS,
                success=True,
                user=user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            # ... rest of login logic
        else:
            # Log failed login
            audit_logger.log_authentication(
                email=email,
                event_type=AuthenticationLog.LOGIN_FAILED,
                success=False,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                failure_reason="Invalid credentials"
            )
    except Exception as e:
        # Log login error
        audit_logger.log_authentication(
            email=email,
            event_type=AuthenticationLog.LOGIN_FAILED,
            success=False,
            ip_address=get_client_ip(request),
            failure_reason=str(e)
        )


# =====================================================
# Example 2: Order State Change Logging
# =====================================================

# Already integrated in apps/orders/services/state_machine.py:
# OrderStateLog model captures all state transitions

# Additional central audit log:
from apps.audit.models import AuditLog

def transition_order_with_audit(order, new_state, user, reason, ip_address):
    """Example with central audit log."""
    old_state = order.state
    
    # Transition order (existing logic)
    StateMachine.transition(order, new_state, user, reason, ip_address)
    
    # Also log to central audit
    audit_logger.log_event(
        category=AuditLog.ORDER,
        action='ORDER_STATE_CHANGE',
        description=f"Order {order.id} transitioned from {old_state} to {new_state}",
        user=user,
        ip_address=ip_address,
        metadata={
            'order_id': str(order.id),
            'old_state': old_state,
            'new_state': new_state,
            'reason': reason
        }
    )


# =====================================================
# Example 3: Admin Action Logging
# =====================================================

# In apps/disputes/views.py (admin decisions):

def refund_buyer_with_logging(request, dispute_id):
    """Example admin decision with logging."""
    dispute = get_object_or_404(Dispute, pk=dispute_id)
    
    # Log admin action
    audit_logger.log_admin_action(
        admin=request.user,
        action='DISPUTE_REFUND_BUYER',
        description=f"Admin refunded buyer for dispute {dispute.id}",
        target_model='Dispute',
        target_id=str(dispute.id),
        metadata={
            'order_id': str(dispute.order.id),
            'buyer_id': str(dispute.order.buyer.id),
            'amount': str(dispute.order.total_amount)
        },
        ip_address=get_client_ip(request)
    )
    
    # Process refund
    DisputeService.refund_buyer_full(dispute, request.user, ...)


# =====================================================
# Example 4: Payment Logging
# =====================================================

# In apps/payments/ (when implemented):

def process_payment_with_logging(order, amount, user, ip_address):
    """Example payment with audit logging."""
    try:
        # Process payment
        payment = PaymentService.process_payment(order, amount)
        
        # Log successful payment
        audit_logger.log_event(
            category=AuditLog.PAYMENT,
            action='PAYMENT_SUCCESS',
            description=f"Payment of {amount} processed for order {order.id}",
            user=user,
            ip_address=ip_address,
            metadata={
                'order_id': str(order.id),
                'amount': str(amount),
                'payment_id': str(payment.id),
                'payment_method': payment.method
            },
            success=True
        )
        
        return payment
        
    except Exception as e:
        # Log payment failure
        audit_logger.log_event(
            category=AuditLog.PAYMENT,
            action='PAYMENT_FAILED',
            description=f"Payment failed for order {order.id}",
            user=user,
            ip_address=ip_address,
            metadata={
                'order_id': str(order.id),
                'amount': str(amount),
                'error': str(e)
            },
            success=False,
            error_message=str(e)
        )
        raise


# =====================================================
# Example 5: Verification Logging
# =====================================================

# In apps/verification/views.py (admin approvals):

def approve_verification_with_logging(request, verification_id):
    """Example verification approval with logging."""
    verification = get_object_or_404(Verification, pk=verification_id)
    
    # Log admin action
    audit_logger.log_admin_action(
        admin=request.user,
        action='VERIFICATION_APPROVED',
        description=f"Admin approved verification for {verification.user.email}",
        target_model='Verification',
        target_id=str(verification.id),
        metadata={
            'user_id': str(verification.user.id),
            'verification_type': verification.verification_type
        },
        ip_address=get_client_ip(request)
    )
    
    # Approve verification
    verification.approve()


# =====================================================
# Example 6: Review Logging
# =====================================================

# In apps/reviews/services/review_service.py:

def create_review_with_logging(order, buyer, rating, ...):
    """Example review creation with logging."""
    review = Review.objects.create(...)
    
    # Log review creation
    audit_logger.log_event(
        category=AuditLog.REVIEW,
        action='REVIEW_CREATED',
        description=f"Buyer {buyer.email} reviewed order {order.id} - {rating} stars",
        user=buyer,
        metadata={
            'order_id': str(order.id),
            'seller_id': str(order.seller.id),
            'rating': rating
        }
    )
    
    return review


# =====================================================
# Example 7: Chat Access Logging
# =====================================================

# Already integrated in apps/chat/models.py:
# ChatAccessLog captures all access attempts

# Additional central audit:
def access_chat_with_logging(user, chat_room, ip_address):
    """Example chat access with logging."""
    # Check access
    can_access = ChatService.can_access_chat(user, chat_room)
    
    # Log to central audit
    audit_logger.log_event(
        category=AuditLog.CHAT,
        action='CHAT_ACCESS',
        description=f"User {user.email} accessed chat for order {chat_room.order.id}",
        user=user,
        ip_address=ip_address,
        metadata={
            'chat_room_id': str(chat_room.id),
            'order_id': str(chat_room.order.id)
        },
        success=can_access
    )
