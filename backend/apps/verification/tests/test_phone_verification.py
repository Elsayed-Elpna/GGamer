"""
Tests for phone verification endpoints.
"""
from django.urls import reverse
from apps.verification.tests.base import BaseVerificationTestCase, APIEndpointTestMixin
from apps.verification.models import PhoneVerification
from common.services.otp import otp_service
from unittest.mock import patch


class PhoneVerificationTestCase(BaseVerificationTestCase, APIEndpointTestMixin):
    """Test cases for phone verification endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.send_otp_url = reverse('verification:send_otp')
        self.verify_otp_url = reverse('verification:verify_otp')
        self.status_url = reverse('verification:phone_status')
    
    # ==================== Send OTP Tests ====================
    
    def test_send_otp_success(self):
        """Test sending OTP with valid phone number."""
        self.authenticate()
        
        data = {'phone_number': '+201012345678'}
        
        with patch.object(otp_service, 'send_otp') as mock_send:
            mock_send.return_value = True
            response = self.client.post(self.send_otp_url, data)
        
        self.assert_response_success(response)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'OTP sent successfully')
    
    def test_send_otp_invalid_phone_format(self):
        """Test sending OTP with invalid phone format."""
        self.authenticate()
        
        invalid_phones = [
            '123456',  # Too short
            '+1234567890',  # Not Egyptian
            '0101234567',  # Missing digit
            'notaphone',  # Not a number
            '+20201234567',  # Invalid Egyptian prefix
        ]
        
        for phone in invalid_phones:
            data = {'phone_number': phone}
            response = self.client.post(self.send_otp_url, data)
            self.assert_response_error(response, 400)
            self.assertIn('phone_number', response.data)
    
    def test_send_otp_unauthenticated(self):
        """Test sending OTP without authentication."""
        self.assert_requires_authentication(self.send_otp_url, 'post')
    
    def test_send_otp_missing_phone_number(self):
        """Test sending OTP without phone number."""
        self.authenticate()
        
        response = self.client.post(self.send_otp_url, {})
        self.assert_response_error(response, 400)
        self.assert_field_required(response, 'phone_number')
    
    def test_send_otp_already_verified_by_another_user(self):
        """Test sending OTP for phone already verified by another user."""
        self.authenticate()
        
        # Create verified phone for another user
        phone_number = '+201012345678'
        self.create_phone_verification(
            user=self.other_user,
            phone_number=phone_number,
            verified=True
        )
        
        data = {'phone_number': phone_number}
        response = self.client.post(self.send_otp_url, data)
        
        self.assert_response_error(response, 400)
        self.assertIn('phone_number', response.data)
    
    def test_send_otp_multiple_times_same_user(self):
        """Test user can request OTP multiple times."""
        self.authenticate()
        
        data = {'phone_number': '+201012345678'}
        
        with patch.object(otp_service, 'send_otp') as mock_send:
            mock_send.return_value = True
            
            # First request
            response1 = self.client.post(self.send_otp_url, data)
            self.assert_response_success(response1)
            
            # Second request
            response2 = self.client.post(self.send_otp_url, data)
            self.assert_response_success(response2)
    
    # ==================== Verify OTP Tests ====================
    
    def test_verify_otp_success(self):
        """Test verifying OTP with correct code."""
        self.authenticate()
        
        phone_number = '+201012345678'
        otp_code = self.get_valid_otp(phone_number)
        
        data = {
            'phone_number': phone_number,
            'otp': otp_code
        }
        
        response = self.client.post(self.verify_otp_url, data)
        
        self.assert_response_success(response)
        self.assertTrue(response.data['verified'])
        
        # Verify phone verification record is created and verified
        phone_verification = PhoneVerification.objects.get(user=self.user)
        self.assertTrue(phone_verification.is_verified)
        self.assertIsNotNone(phone_verification.verified_at)
    
    def test_verify_otp_invalid_code(self):
        """Test verifying OTP with incorrect code."""
        self.authenticate()
        
        phone_number = '+201012345678'
        # Generate valid OTP but use wrong code
        self.get_valid_otp(phone_number)
        
        data = {
            'phone_number': phone_number,
            'otp': '000000'  # Wrong code
        }
        
        response = self.client.post(self.verify_otp_url, data)
        
        self.assert_response_error(response, 400)
    
    def test_verify_otp_expired(self):
        """Test verifying expired OTP."""
        self.authenticate()
        
        phone_number = '+201012345678'
        otp_code = self.get_valid_otp(phone_number)
        
        # Mock OTP as expired
        with patch.object(otp_service, 'verify_otp') as mock_verify:
            mock_verify.return_value = False
            
            data = {
                'phone_number': phone_number,
                'otp': otp_code
            }
            
            response = self.client.post(self.verify_otp_url, data)
            
            self.assert_response_error(response, 400)
    
    def test_verify_otp_unauthenticated(self):
        """Test verifying OTP without authentication."""
        self.assert_requires_authentication(self.verify_otp_url, 'post')
    
    def test_verify_otp_missing_fields(self):
        """Test verifying OTP with missing fields."""
        self.authenticate()
        
        # Missing phone number
        response = self.client.post(self.verify_otp_url, {'otp': '123456'})
        self.assert_response_error(response, 400)
        self.assert_field_required(response, 'phone_number')
        
        # Missing OTP
        response = self.client.post(self.verify_otp_url, {'phone_number': '+201012345678'})
        self.assert_response_error(response, 400)
        self.assert_field_required(response, 'otp')
    
    def test_verify_otp_invalid_otp_length(self):
        """Test verifying OTP with invalid length."""
        self.authenticate()
        
        data = {
            'phone_number': '+201012345678',
            'otp': '123'  # Too short
        }
        
        response = self.client.post(self.verify_otp_url, data)
        self.assert_response_error(response, 400)
    
    # ==================== Phone Status Tests ====================
    
    def test_phone_status_verified(self):
        """Test getting status for verified phone."""
        self.authenticate()
        
        # Create verified phone
        phone_number = '+201012345678'
        self.create_phone_verification(
            user=self.user,
            phone_number=phone_number,
            verified=True
        )
        
        response = self.client.get(self.status_url)
        
        self.assert_response_success(response)
        self.assertTrue(response.data['is_verified'])
        self.assertIsNotNone(response.data['phone_number'])
        self.assertIsNotNone(response.data['verified_at'])
        
        # Check phone is masked
        self.assertIn('****', response.data['phone_number'])
    
    def test_phone_status_not_verified(self):
        """Test getting status for unverified phone."""
        self.authenticate()
        
        # Create unverified phone
        self.create_phone_verification(
            user=self.user,
            phone_number='+201012345678',
            verified=False
        )
        
        response = self.client.get(self.status_url)
        
        self.assert_response_success(response)
        self.assertFalse(response.data['is_verified'])
    
    def test_phone_status_no_verification(self):
        """Test getting status when no verification exists."""
        self.authenticate()
        
        response = self.client.get(self.status_url)
        
        self.assert_response_success(response)
        self.assertFalse(response.data['is_verified'])
        self.assertIsNone(response.data['phone_number'])
        self.assertIsNone(response.data['verified_at'])
    
    def test_phone_status_unauthenticated(self):
        """Test getting status without authentication."""
        self.assert_requires_authentication(self.status_url, 'get')
    
    def test_phone_status_different_user(self):
        """Test users can only see their own phone status."""
        self.authenticate()
        
        # Create verification for another user
        self.create_phone_verification(
            user=self.other_user,
            phone_number='+201012345678',
            verified=True
        )
        
        # Current user should not see other user's verification
        response = self.client.get(self.status_url)
        
        self.assert_response_success(response)
        self.assertFalse(response.data['is_verified'])
