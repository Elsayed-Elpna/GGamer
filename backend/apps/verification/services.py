"""
Verification service for handling seller verification workflow.
Includes duplicate detection, approval/rejection, and permission checks.
"""
from django.db import transaction
from django.utils import timezone
from apps.verification.models import SellerVerification, VerificationAuditLog
from common.services.encryption import encryption_service
import logging

logger = logging.getLogger(__name__)


class VerificationService:
    """Service for managing seller verification workflow"""
    
    @staticmethod
    def check_duplicate_national_id(national_id: str, exclude_user_id=None) -> bool:
        """
        Check if national ID is already used by another user.
        
        Args:
            national_id: Plain text national ID
            exclude_user_id: User ID to exclude from check (for updates)
            
        Returns:
            True if duplicate found, False otherwise
        """
        national_id_hash = encryption_service.hash_national_id(national_id)
        
        query = SellerVerification.objects.filter(national_id_hash=national_id_hash)
        
        if exclude_user_id:
            query = query.exclude(user_id=exclude_user_id)
        
        return query.exists()
    
    @staticmethod
    @transaction.atomic
    def submit_seller_verification(user, national_id: str, date_of_birth, 
                                   id_front_photo, id_back_photo, selfie_photo,
                                   billing_address=None, ip_address=None) -> SellerVerification:
        """
        Submit seller verification for review.
        
        Args:
            user: User instance
            national_id: Plain text national ID
            date_of_birth: Date of birth
            id_front_photo: Front photo of ID
            id_back_photo: Back photo of ID
            selfie_photo: Selfie with ID
            billing_address: Optional billing address
            ip_address: IP address of requester
            
        Returns:
            SellerVerification instance
            
        Raises:
            ValueError: If duplicate national ID found
        """
        # Check for duplicate national ID
        if VerificationService.check_duplicate_national_id(national_id, exclude_user_id=user.id):
            raise ValueError("This National ID is already registered with another account")
        
        # Check if user already has verification
        try:
            verification = SellerVerification.objects.get(user=user)
            
            # If rejected, allow resubmission
            if verification.status == SellerVerification.VerificationStatus.REJECTED:
                # Update existing verification
                verification.set_national_id(national_id)
                verification.date_of_birth = date_of_birth
                verification.billing_address = billing_address
                verification.id_front_photo = id_front_photo
                verification.id_back_photo = id_back_photo
                verification.selfie_photo = selfie_photo
                verification.status = SellerVerification.VerificationStatus.RESUBMITTED
                verification.rejection_reason = None
                verification.reviewed_by = None
                verification.reviewed_at = None
                verification.save()
                
                action = VerificationAuditLog.Action.RESUBMIT
            else:
                raise ValueError("Verification already submitted and pending review")
        
        except SellerVerification.DoesNotExist:
            # Create new verification
            verification = SellerVerification(
                user=user,
                date_of_birth=date_of_birth,
                billing_address=billing_address,
                id_front_photo=id_front_photo,
                id_back_photo=id_back_photo,
                selfie_photo=selfie_photo,
                status=SellerVerification.VerificationStatus.PENDING
            )
            verification.set_national_id(national_id)
            
            # Set photo type for upload path
            verification._photo_type = 'id_front'
            verification.id_front_photo = id_front_photo
            verification._photo_type = 'id_back'
            verification.id_back_photo = id_back_photo
            verification._photo_type = 'selfie'
            verification.selfie_photo = selfie_photo
            
            verification.save()
            
            action = VerificationAuditLog.Action.SUBMIT
        
        # Create audit log
        VerificationAuditLog.objects.create(
            user=user,
            action=action,
            details={
                'date_of_birth': str(date_of_birth),
                'has_billing_address': bool(billing_address)
            },
            ip_address=ip_address
        )
        
        logger.info(f"Seller verification submitted for user {user.email}")
        
        return verification
    
    @staticmethod
    @transaction.atomic
    def approve_verification(verification_id: int, admin_user, ip_address=None) -> SellerVerification:
        """
        Approve seller verification.
        
        Args:
            verification_id: SellerVerification ID
            admin_user: Admin/Support user approving
            ip_address: IP address of admin
            
        Returns:
            Updated SellerVerification instance
        """
        verification = SellerVerification.objects.select_for_update().get(id=verification_id)
        
        if verification.status == SellerVerification.VerificationStatus.APPROVED:
            raise ValueError("Verification already approved")
        
        verification.approve(admin_user)
        
        # Create audit log
        VerificationAuditLog.objects.create(
            user=verification.user,
            action=VerificationAuditLog.Action.APPROVE,
            performed_by=admin_user,
            details={
                'verification_id': verification_id
            },
            ip_address=ip_address
        )
        
        logger.info(f"Seller verification approved for user {verification.user.email} by {admin_user.email}")
        
        return verification
    
    @staticmethod
    @transaction.atomic
    def reject_verification(verification_id: int, admin_user, reason: str, ip_address=None) -> SellerVerification:
        """
        Reject seller verification.
        
        Args:
            verification_id: SellerVerification ID
            admin_user: Admin/Support user rejecting
            reason: Reason for rejection
            ip_address: IP address of admin
            
        Returns:
            Updated SellerVerification instance
        """
        if not reason or len(reason.strip()) < 10:
            raise ValueError("Rejection reason must be at least 10 characters")
        
        verification = SellerVerification.objects.select_for_update().get(id=verification_id)
        
        verification.reject(admin_user, reason)
        
        # Create audit log
        VerificationAuditLog.objects.create(
            user=verification.user,
            action=VerificationAuditLog.Action.REJECT,
            performed_by=admin_user,
            details={
                'verification_id': verification_id,
                'reason': reason
            },
            ip_address=ip_address
        )
        
        logger.info(f"Seller verification rejected for user {verification.user.email} by {admin_user.email}")
        
        return verification
    
    @staticmethod
    def can_create_offers(user) -> tuple[bool, str]:
        """
        Check if user can create offers (requires verification).
        
        Args:
            user: User instance
            
        Returns:
            Tuple of (can_create: bool, message: str)
        """
        # Check phone verification
        if not hasattr(user, 'phone_verification') or not user.phone_verification.is_verified:
            return False, "Phone number must be verified to create offers"
        
        # Check seller verification
        if not hasattr(user, 'seller_verification'):
            return False, "Seller verification required to create offers"
        
        verification = user.seller_verification
        
        if verification.status == SellerVerification.VerificationStatus.PENDING:
            return False, "Seller verification is pending review"
        
        if verification.status == SellerVerification.VerificationStatus.RESUBMITTED:
            return False, "Seller verification is pending review"
        
        if verification.status == SellerVerification.VerificationStatus.REJECTED:
            return False, f"Seller verification was rejected: {verification.rejection_reason}"
        
        if not verification.is_verified:
            return False, "Seller verification required to create offers"
        
        return True, "User is verified and can create offers"


# Singleton instance
verification_service = VerificationService()
