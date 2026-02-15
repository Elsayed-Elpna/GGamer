"""
Tests for admin verification endpoints.
"""
from django.urls import reverse
from apps.verification.tests.base import BaseVerificationTestCase, APIEndpointTestMixin
from apps.verification.models import SellerVerification, VerificationAuditLog
from common.models import AdminActionLog


class AdminVerificationTestCase(BaseVerificationTestCase, APIEndpointTestMixin):
    """Test cases for admin verification endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.list_pending_url = reverse('verification:list_pending')
    
    def get_details_url(self, verification_id):
        """Get URL for verification details."""
        return reverse('verification:verification_details', kwargs={'verification_id': verification_id})
    
    def get_approve_url(self, verification_id):
        """Get URL for approving verification."""
        return reverse('verification:approve_verification', kwargs={'verification_id': verification_id})
    
    def get_reject_url(self, verification_id):
        """Get URL for rejecting verification."""
        return reverse('verification:reject_verification', kwargs={'verification_id': verification_id})
    
    # ==================== List Pending Verifications Tests ====================
    
    def test_list_pending_verifications_admin(self):
        """Test admin can list pending verifications."""
        self.authenticate(self.admin_user)
        
        # Create pending verifications
        v1 = self.create_seller_verification(user=self.user, status='PENDING')
        v2 = self.create_seller_verification(user=self.other_user, status='PENDING')
        
        # Create approved verification (should not appear)
        v3 = self.create_seller_verification(
            user=User.objects.create_user(
                email='user3@example.com',
                password='Pass123!'
            ),
            status='APPROVED'
        )
        
        response = self.client.get(self.list_pending_url)
        
        self.assert_response_success(response)
        self.assertEqual(len(response.data), 2)
        
        # Check response contains expected data
        ids = [item['id'] for item in response.data]
        self.assertIn(v1.id, ids)
        self.assertIn(v2.id, ids)
        self.assertNotIn(v3.id, ids)
    
    def test_list_pending_verifications_support(self):
        """Test support user can list pending verifications."""
        self.authenticate(self.support_user)
        
        self.create_seller_verification(user=self.user, status='PENDING')
        
        response = self.client.get(self.list_pending_url)
        
        self.assert_response_success(response)
        self.assertGreater(len(response.data), 0)
    
    def test_list_pending_verifications_non_admin(self):
        """Test regular user cannot list pending verifications."""
        self.assert_requires_admin(self.list_pending_url, 'get')
    
    def test_list_pending_verifications_unauthenticated(self):
        """Test unauthenticated user cannot list verifications."""
        self.assert_requires_authentication(self.list_pending_url, 'get')
    
    def test_list_pending_includes_resubmitted(self):
        """Test list includes resubmitted verifications."""
        self.authenticate(self.admin_user)
        
        v1 = self.create_seller_verification(user=self.user, status='PENDING')
        v2 = self.create_seller_verification(user=self.other_user, status='RESUBMITTED')
        
        response = self.client.get(self.list_pending_url)
        
        self.assert_response_success(response)
        ids = [item['id'] for item in response.data]
        self.assertIn(v1.id, ids)
        self.assertIn(v2.id, ids)
    
    # ==================== Get Verification Details Tests ====================
    
    def test_get_verification_details_admin(self):
        """Test admin can view verification details."""
        self.authenticate(self.admin_user)
        
        verification = self.create_seller_verification(user=self.user, status='PENDING')
        url = self.get_details_url(verification.id)
        
        response = self.client.get(url)
        
        self.assert_response_success(response)
        self.assertEqual(response.data['id'], verification.id)
        self.assertIn('national_id_masked', response.data)
        
        # Check admin action was logged
        log_exists = AdminActionLog.objects.filter(
            admin_user=self.admin_user,
            action=AdminActionLog.Action.VIEW_SENSITIVE_DATA,
            target_user=self.user
        ).exists()
        self.assertTrue(log_exists)
    
    def test_get_verification_details_non_admin(self):
        """Test regular user cannot view verification details."""
        verification = self.create_seller_verification(user=self.other_user, status='PENDING')
        url = self.get_details_url(verification.id)
        
        self.assert_requires_admin(url, 'get')
    
    def test_get_verification_details_not_found(self):
        """Test getting details for non-existent verification."""
        self.authenticate(self.admin_user)
        
        url = self.get_details_url(99999)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_get_verification_details_unauthenticated(self):
        """Test unauthenticated user cannot view details."""
        verification = self.create_seller_verification(user=self.user, status='PENDING')
        url = self.get_details_url(verification.id)
        
        self.assert_requires_authentication(url, 'get')
    
    # ==================== Approve Verification Tests ====================
    
    def test_approve_verification_success(self):
        """Test admin can approve verification."""
        self.authenticate(self.admin_user)
        
        verification = self.create_seller_verification(user=self.user, status='PENDING')
        url = self.get_approve_url(verification.id)
        
        response = self.client.post(url)
        
        self.assert_response_success(response)
        self.assertIn('message', response.data)
        
        # Verify status changed
        verification.refresh_from_db()
        self.assertEqual(verification.status, 'APPROVED')
        self.assertEqual(verification.reviewed_by, self.admin_user)
        self.assertIsNotNone(verification.reviewed_at)
        
        # Check admin action was logged
        log_exists = AdminActionLog.objects.filter(
            admin_user=self.admin_user,
            action=AdminActionLog.Action.APPROVE_VERIFICATION,
            target_user=self.user
        ).exists()
        self.assertTrue(log_exists)
        
        # Check audit log created
        audit_exists = VerificationAuditLog.objects.filter(
            verification=verification,
            action='APPROVED',
            performed_by=self.admin_user
        ).exists()
        self.assertTrue(audit_exists)
    
    def test_approve_verification_non_admin(self):
        """Test regular user cannot approve verification."""
        verification = self.create_seller_verification(user=self.other_user, status='PENDING')
        url = self.get_approve_url(verification.id)
        
        self.assert_requires_admin(url, 'post')
    
    def test_approve_verification_not_found(self):
        """Test approving non-existent verification."""
        self.authenticate(self.admin_user)
        
        url = self.get_approve_url(99999)
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_approve_already_approved(self):
        """Test approving already approved verification."""
        self.authenticate(self.admin_user)
        
        verification = self.create_seller_verification(user=self.user, status='APPROVED')
        verification.approve(self.admin_user)
        
        url = self.get_approve_url(verification.id)
        response = self.client.post(url)
        
        # Should still succeed (idempotent)
        self.assert_response_success(response)
    
    def test_approve_verification_unauthenticated(self):
        """Test unauthenticated user cannot approve."""
        verification = self.create_seller_verification(user=self.user, status='PENDING')
        url = self.get_approve_url(verification.id)
        
        self.assert_requires_authentication(url, 'post')
    
    # ==================== Reject Verification Tests ====================
    
    def test_reject_verification_success(self):
        """Test admin can reject verification with reason."""
        self.authenticate(self.admin_user)
        
        verification = self.create_seller_verification(user=self.user, status='PENDING')
        url = self.get_reject_url(verification.id)
        
        data = {'reason': 'Documents are not clear'}
        response = self.client.post(url, data)
        
        self.assert_response_success(response)
        self.assertIn('message', response.data)
        
        # Verify status changed
        verification.refresh_from_db()
        self.assertEqual(verification.status, 'REJECTED')
        self.assertEqual(verification.rejection_reason, 'Documents are not clear')
        self.assertEqual(verification.reviewed_by, self.admin_user)
        
        # Check admin action was logged
        log_exists = AdminActionLog.objects.filter(
            admin_user=self.admin_user,
            action=AdminActionLog.Action.REJECT_VERIFICATION,
            target_user=self.user
        ).exists()
        self.assertTrue(log_exists)
        
        # Check audit log created
        audit_exists = VerificationAuditLog.objects.filter(
            verification=verification,
            action='REJECTED',
            performed_by=self.admin_user
        ).exists()
        self.assertTrue(audit_exists)
    
    def test_reject_verification_missing_reason(self):
        """Test rejecting without reason fails."""
        self.authenticate(self.admin_user)
        
        verification = self.create_seller_verification(user=self.user, status='PENDING')
        url = self.get_reject_url(verification.id)
        
        response = self.client.post(url, {})
        
        self.assert_response_error(response, 400)
        self.assertIn('detail', response.data)
    
    def test_reject_verification_non_admin(self):
        """Test regular user cannot reject verification."""
        verification = self.create_seller_verification(user=self.other_user, status='PENDING')
        url = self.get_reject_url(verification.id)
        
        data = {'reason': 'Invalid documents'}
        self.assert_requires_admin(url, 'post', data)
    
    def test_reject_verification_not_found(self):
        """Test rejecting non-existent verification."""
        self.authenticate(self.admin_user)
        
        url = self.get_reject_url(99999)
        data = {'reason': 'Invalid documents'}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 404)
    
    def test_reject_verification_unauthenticated(self):
        """Test unauthenticated user cannot reject."""
        verification = self.create_seller_verification(user=self.user, status='PENDING')
        url = self.get_reject_url(verification.id)
        
        self.assert_requires_authentication(url, 'post')
    
    def test_reject_already_rejected(self):
        """Test rejecting already rejected verification."""
        self.authenticate(self.admin_user)
        
        verification = self.create_seller_verification(user=self.user, status='REJECTED')
        verification.reject(self.admin_user, 'First reason')
        
        url = self.get_reject_url(verification.id)
        data = {'reason': 'Second reason'}
        response = self.client.post(url, data)
        
        # Should still succeed (idempotent)
        self.assert_response_success(response)
        
        # Reason should be updated
        verification.refresh_from_db()
        self.assertEqual(verification.rejection_reason, 'Second reason')


# Import User model
from django.contrib.auth import get_user_model
User = get_user_model()
