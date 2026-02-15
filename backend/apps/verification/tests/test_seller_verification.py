"""
Tests for seller verification endpoints.
"""
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.verification.tests.base import BaseVerificationTestCase, APIEndpointTestMixin
from apps.verification.models import SellerVerification
from unittest.mock import patch


class SellerVerificationTestCase(BaseVerificationTestCase, APIEndpointTestMixin):
    """Test cases for seller verification endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.submit_url = reverse('verification:submit_seller_verification')
        self.status_url = reverse('verification:seller_status')
        self.can_create_offers_url = reverse('verification:can_create_offers')
    
    def get_valid_seller_data(self):
        """Get valid seller verification data."""
        return {
            'national_id': '12345678901234',
            'date_of_birth': '1990-01-01',
            'billing_address': '123 Test St, Cairo, Egypt',
            'id_front_photo': self.create_test_image('id_front.jpg'),
            'id_back_photo': self.create_test_image('id_back.jpg'),
            'selfie_photo': self.create_test_image('selfie.jpg'),
        }
    
    # ==================== Submit Verification Tests ====================
    
    def test_submit_verification_success(self):
        """Test submitting seller verification with valid data."""
        self.authenticate()
        
        data = self.get_valid_seller_data()
        response = self.client.post(self.submit_url, data, format='multipart')
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['status'], 'PENDING')
        
        # Verify record created
        verification = SellerVerification.objects.get(user=self.user)
        self.assertEqual(verification.status, 'PENDING')
        self.assertIsNotNone(verification.national_id)
    
    def test_submit_verification_invalid_national_id(self):
        """Test submitting with invalid national ID format."""
        self.authenticate()
        
        invalid_ids = [
            '123',  # Too short
            '12345678901234567890',  # Too long
            'abcdefghijklmn',  # Not numeric
            '1234567890123',  # 13 digits instead of 14
        ]
        
        for invalid_id in invalid_ids:
            data = self.get_valid_seller_data()
            data['national_id'] = invalid_id
            
            response = self.client.post(self.submit_url, data, format='multipart')
            self.assert_response_error(response, 400)
            self.assertIn('national_id', response.data)
    
    def test_submit_verification_missing_documents(self):
        """Test submitting without required documents."""
        self.authenticate()
        
        # Missing id_front_photo
        data = self.get_valid_seller_data()
        del data['id_front_photo']
        response = self.client.post(self.submit_url, data, format='multipart')
        self.assert_response_error(response, 400)
        self.assert_field_required(response, 'id_front_photo')
        
        # Missing id_back_photo
        data = self.get_valid_seller_data()
        del data['id_back_photo']
        response = self.client.post(self.submit_url, data, format='multipart')
        self.assert_response_error(response, 400)
        self.assert_field_required(response, 'id_back_photo')
        
        # Missing selfie_photo
        data = self.get_valid_seller_data()
        del data['selfie_photo']
        response = self.client.post(self.submit_url, data, format='multipart')
        self.assert_response_error(response, 400)
        self.assert_field_required(response, 'selfie_photo')
    
    def test_submit_verification_duplicate(self):
        """Test submitting when verification already exists."""
        self.authenticate()
        
        # Create existing verification
        self.create_seller_verification(user=self.user, status='PENDING')
        
        # Try to submit again
        data = self.get_valid_seller_data()
        response = self.client.post(self.submit_url, data, format='multipart')
        
        self.assert_response_error(response, 400)
    
    def test_submit_verification_unauthenticated(self):
        """Test submitting without authentication."""
        self.assert_requires_authentication(self.submit_url, 'post')
    
    def test_submit_verification_missing_required_fields(self):
        """Test submitting with missing required fields."""
        self.authenticate()
        
        required_fields = ['national_id', 'date_of_birth', 'billing_address']
        
        for field in required_fields:
            data = self.get_valid_seller_data()
            del data[field]
            
            response = self.client.post(self.submit_url, data, format='multipart')
            self.assert_response_error(response, 400)
            self.assert_field_required(response, field)
    
    def test_submit_verification_invalid_date_of_birth(self):
        """Test submitting with invalid date of birth."""
        self.authenticate()
        
        invalid_dates = [
            'invalid-date',
            '2025-01-01',  # Future date
            '1800-01-01',  # Too old
        ]
        
        for invalid_date in invalid_dates:
            data = self.get_valid_seller_data()
            data['date_of_birth'] = invalid_date
            
            response = self.client.post(self.submit_url, data, format='multipart')
            self.assert_response_error(response, 400)
    
    def test_submit_verification_national_id_already_used(self):
        """Test submitting with national ID already used by another user."""
        self.authenticate()
        
        national_id = '12345678901234'
        
        # Create verification for another user with same national ID
        self.create_seller_verification(
            user=self.other_user,
            status='APPROVED',
            national_id=national_id
        )
        
        # Try to submit with same national ID
        data = self.get_valid_seller_data()
        data['national_id'] = national_id
        
        response = self.client.post(self.submit_url, data, format='multipart')
        self.assert_response_error(response, 400)
        self.assertIn('national_id', response.data)
    
    # ==================== Seller Status Tests ====================
    
    def test_seller_status_pending(self):
        """Test getting status for pending verification."""
        self.authenticate()
        
        self.create_seller_verification(user=self.user, status='PENDING')
        
        response = self.client.get(self.status_url)
        
        self.assert_response_success(response)
        self.assertEqual(response.data['status'], 'PENDING')
        self.assertIn('status_display', response.data)
        
        # Check national ID is masked
        self.assertIn('national_id_masked', response.data)
        self.assertIn('****', response.data['national_id_masked'])
    
    def test_seller_status_approved(self):
        """Test getting status for approved verification."""
        self.authenticate()
        
        verification = self.create_seller_verification(user=self.user, status='APPROVED')
        verification.approve(self.admin_user)
        
        response = self.client.get(self.status_url)
        
        self.assert_response_success(response)
        self.assertEqual(response.data['status'], 'APPROVED')
        self.assertIsNotNone(response.data['reviewed_at'])
    
    def test_seller_status_rejected(self):
        """Test getting status for rejected verification."""
        self.authenticate()
        
        verification = self.create_seller_verification(user=self.user, status='REJECTED')
        verification.reject(self.admin_user, 'Invalid documents')
        
        response = self.client.get(self.status_url)
        
        self.assert_response_success(response)
        self.assertEqual(response.data['status'], 'REJECTED')
        self.assertIn('rejection_reason', response.data)
    
    def test_seller_status_not_found(self):
        """Test getting status when no verification exists."""
        self.authenticate()
        
        response = self.client.get(self.status_url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_seller_status_unauthenticated(self):
        """Test getting status without authentication."""
        self.assert_requires_authentication(self.status_url, 'get')
    
    def test_seller_status_different_user(self):
        """Test users can only see their own verification status."""
        self.authenticate()
        
        # Create verification for another user
        self.create_seller_verification(user=self.other_user, status='APPROVED')
        
        # Current user should get 404
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 404)
    
    # ==================== Can Create Offers Tests ====================
    
    def test_can_create_offers_approved(self):
        """Test verified seller can create offers."""
        self.authenticate()
        
        verification = self.create_seller_verification(user=self.user, status='APPROVED')
        verification.approve(self.admin_user)
        
        response = self.client.get(self.can_create_offers_url)
        
        self.assert_response_success(response)
        self.assertTrue(response.data['can_create_offers'])
        self.assertIsNone(response.data['reason'])
    
    def test_can_create_offers_pending(self):
        """Test user with pending verification cannot create offers."""
        self.authenticate()
        
        self.create_seller_verification(user=self.user, status='PENDING')
        
        response = self.client.get(self.can_create_offers_url)
        
        self.assert_response_success(response)
        self.assertFalse(response.data['can_create_offers'])
        self.assertIsNotNone(response.data['reason'])
    
    def test_can_create_offers_rejected(self):
        """Test user with rejected verification cannot create offers."""
        self.authenticate()
        
        verification = self.create_seller_verification(user=self.user, status='REJECTED')
        verification.reject(self.admin_user, 'Invalid documents')
        
        response = self.client.get(self.can_create_offers_url)
        
        self.assert_response_success(response)
        self.assertFalse(response.data['can_create_offers'])
        self.assertIsNotNone(response.data['reason'])
    
    def test_can_create_offers_not_submitted(self):
        """Test user without verification cannot create offers."""
        self.authenticate()
        
        response = self.client.get(self.can_create_offers_url)
        
        self.assert_response_success(response)
        self.assertFalse(response.data['can_create_offers'])
        self.assertEqual(response.data['reason'], 'Seller verification not submitted')
    
    def test_can_create_offers_unauthenticated(self):
        """Test checking offers without authentication."""
        self.assert_requires_authentication(self.can_create_offers_url, 'get')
