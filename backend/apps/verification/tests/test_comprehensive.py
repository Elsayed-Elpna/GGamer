"""
Comprehensive test suite for all verification endpoints.
Focus: Security-first testing with complete coverage.

Test Categories:
1. Security Tests (SQL injection, XSS, auth bypass, etc.)
2. Functional Tests (all endpoints)
3. Rate Limiting Tests
4. Integration Tests
5. Edge Cases
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.verification.models import PhoneVerification, SellerVerification, VerificationAuditLog
from apps.accounts.models import PrivateProfile
from PIL import Image
import io
import json

User = get_user_model()


class BaseVerificationTest(TestCase):
    """Base test class with common setup"""
    
    def setUp(self):
        """Setup test data"""
        cache.clear()  # Clear cache before each test
        
        # Create test users
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='TestPass123!',
            is_active=True
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='AdminPass123!',
            is_active=True,
            is_staff=True
        )
        
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='OtherPass123!',
            is_active=True
        )
        
        # Setup API clients
        self.client = APIClient()
        self.admin_client = APIClient()
        
        # Authenticate
        self.client.force_authenticate(user=self.user)
        self.admin_client.force_authenticate(user=self.admin_user)
        
        # Endpoint URLs
        self.send_otp_url = '/api/verification/phone/send-otp/'
        self.verify_otp_url = '/api/verification/phone/verify-otp/'
        self.phone_status_url = '/api/verification/phone/status/'
        self.submit_seller_url = '/api/verification/seller/submit/'
        self.seller_status_url = '/api/verification/seller/status/'
        self.can_create_offers_url = '/api/verification/seller/can-create-offers/'
        self.admin_pending_url = '/api/verification/admin/pending/'
        
    def create_test_image(self, filename='test.jpg', size=(500, 500)):
        """Create a test image file"""
        file = io.BytesIO()
        image = Image.new('RGB', size, color='red')
        image.save(file, 'JPEG')
        file.seek(0)
        return SimpleUploadedFile(filename, file.read(), content_type='image/jpeg')
    
    def tearDown(self):
        """Cleanup"""
        cache.clear()


# =============================================================================
# SECURITY TESTS - CRITICAL
# =============================================================================

class SecurityTests(BaseVerificationTest):
    """Critical security vulnerability tests"""
    
    def test_sql_injection_phone_number(self):
        """Test SQL injection in phone number field"""
        malicious_payloads = [
            "'; DROP TABLE phone_verifications; --",
            "1' OR '1'='1",
            "+1234' UNION SELECT * FROM users--",
            "+1234\"; DELETE FROM phone_verifications WHERE \"1\"=\"1",
        ]
        
        for payload in malicious_payloads:
            response = self.client.post(self.send_otp_url, {
                'phone_number': payload
            })
            # Should reject with validation error, not execute SQL
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('phone_number', response.data)
        
        # Verify tables still exist
        self.assertEqual(PhoneVerification.objects.count(), 0)
    
    def test_sql_injection_national_id(self):
        """Test SQL injection in national ID field"""
        malicious_payloads = [
            "'; DROP TABLE seller_verifications; --",
            "A12345' OR '1'='1",
            "ABC123\"; DELETE FROM users--",
        ]
        
        for payload in malicious_payloads:
            response = self.client.post(self.submit_seller_url, {
                'national_id': payload,
                'date_of_birth': '1990-01-01',
                'billing_address': 'Test',
                'id_front_photo': self.create_test_image(),
                'id_back_photo': self.create_test_image(),
                'selfie_photo': self.create_test_image(),
            })
            # Should handle gracefully
            self.assertIn(response.status_code, [400, 413])  # Validation error or too large
    
    def test_xss_in_billing_address(self):
        """Test XSS protection in billing address"""
        xss_payloads = [
            '<script>alert("XSS")</script>',
            '<img src=x onerror=alert("XSS")>',
            'javascript:alert("XSS")',
            '<iframe src="javascript:alert(\'XSS\')"></iframe>',
        ]
        
        for payload in xss_payloads:
            response = self.client.post(self.submit_seller_url, {
                'national_id': 'TEST123',
                'date_of_birth': '1990-01-01',
                'billing_address': payload,
                'id_front_photo': self.create_test_image(),
                'id_back_photo': self.create_test_image(),
                'selfie_photo': self.create_test_image(),
            })
            # Should accept (Django handles escaping)
            # But verify no script execution possible
            if response.status_code == 201:
                verification = SellerVerification.objects.get(user=self.user)
                # Address should be stored as-is (escaping happens on output)
                self.assertEqual(verification.billing_address, payload)
    
    def test_authentication_required(self):
        """Test all endpoints require authentication"""
        anon_client = APIClient()
        
        endpoints = [
            ('POST', self.send_otp_url, {'phone_number': '+1234567890'}),
            ('POST', self.verify_otp_url, {'phone_number': '+1234567890', 'otp': '123456'}),
            ('GET', self.phone_status_url, None),
            ('POST', self.submit_seller_url, {}),
            ('GET', self.seller_status_url, None),
            ('GET', self.can_create_offers_url, None),
        ]
        
        for method, url, data in endpoints:
            if method == 'POST':
                response = anon_client.post(url, data)
            else:
                response = anon_client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED,
                           f"Endpoint {url} should require authentication")
    
    def test_admin_authorization_required(self):
        """Test admin endpoints require admin role"""
        admin_endpoints = [
            ('GET', self.admin_pending_url),
            ('GET', '/api/verification/admin/details/1/'),
            ('POST', '/api/verification/admin/approve/1/'),
            ('POST', '/api/verification/admin/reject/1/'),
        ]
        
        for method, url in admin_endpoints:
            if method == 'POST':
                response = self.client.post(url, {'reason': 'test'})
            else:
                response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                           f"Non-admin should not access {url}")
    
    def test_otp_brute_force_protection(self):
        """Test OTP brute force protection (attempt limiting)"""
        # First send OTP
        self.client.post(self.send_otp_url, {'phone_number': '+1234567890'})
        
        # Try wrong OTP 3 times (should work)
        for i in range(3):
            response = self.client.post(self.verify_otp_url, {
                'phone_number': '+1234567890',
                'otp': f'99999{i}'
            })
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # 4th attempt should be blocked by cache
        response = self.client.post(self.verify_otp_url, {
            'phone_number': '+1234567890',
            'otp': '999999'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Too many failed attempts', str(response.data))
    
    def test_otp_rate_limiting(self):
        """Test OTP send rate limiting (5/hour)"""
        phone = '+1234567890'
        
        # Should allow 5 OTP requests
        for i in range(5):
            response = self.client.post(self.send_otp_url, {'phone_number': phone})
            self.assertIn(response.status_code, [200, 400])  # May fail validation
        
        # 6th request should be throttled
        response = self.client.post(self.send_otp_url, {'phone_number': phone})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
    
    def test_otp_verify_rate_limiting(self):
        """Test OTP verify rate limiting (3/hour)"""
        # Send OTP first
        self.client.post(self.send_otp_url, {'phone_number': '+1234567890'})
        
        # Try to verify 3 times (allowed)
        for i in range(3):
            response = self.client.post(self.verify_otp_url, {
                'phone_number': '+1234567890',
                'otp': '123456'
            })
            self.assertIn(response.status_code, [200, 400])
        
        # 4th attempt should be throttled
        response = self.client.post(self.verify_otp_url, {
            'phone_number': '+1234567890',
            'otp': '123456'
        })
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
    
    def test_file_upload_security(self):
        """Test file upload accepts only images"""
        # Test with malicious file (PHP script)
        malicious_file = SimpleUploadedFile(
            'hack.php',
            b'<?php system($_GET["cmd"]); ?>',
            content_type='image/jpeg'  # Fake content type
        )
        
        response = self.client.post(self.submit_seller_url, {
            'national_id': 'TEST123',
            'date_of_birth': '1990-01-01',
            'billing_address': 'Test Address',
            'id_front_photo': malicious_file,
            'id_back_photo': self.create_test_image(),
            'selfie_photo': self.create_test_image(),
        })
        
        # Should reject (magic byte validation)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_file_upload_size_limit(self):
        """Test file upload size limits (max 5MB)"""
        # Create oversized image (>5MB)
        large_file = io.BytesIO()
        large_image = Image.new('RGB', (5000, 5000), color='blue')
        large_image.save(large_file, 'JPEG', quality=95)
        large_file.seek(0)
        
        oversized = SimpleUploadedFile('large.jpg', large_file.read()[:6*1024*1024])  # 6MB
        
        response = self.client.post(self.submit_seller_url, {
            'national_id': 'TEST123',
            'date_of_birth': '1990-01-01',
            'billing_address': 'Test',
            'id_front_photo': oversized,
            'id_back_photo': self.create_test_image(),
            'selfie_photo': self.create_test_image(),
        })
        
        # Should reject
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_national_id_case_sensitivity_bypass(self):
        """Test national ID normalization prevents case bypass"""
        # Create verification with lowercase ID
        response1 = self.client.post(self.submit_seller_url, {
            'national_id': 'abc123def',
            'date_of_birth': '1990-01-01',
            'billing_address': 'Test',
            'id_front_photo': self.create_test_image(),
            'id_back_photo': self.create_test_image(),
            'selfie_photo': self.create_test_image(),
        })
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Try to create another with uppercase (should fail - normalized to same)
        other_client = APIClient()
        other_client.force_authenticate(user=self.other_user)
        
        response2 = other_client.post(self.submit_seller_url, {
            'national_id': 'ABC123DEF',  # Same ID, different case
            'date_of_birth': '1990-01-01',
            'billing_address': 'Test',
            'id_front_photo': self.create_test_image(),
            'id_back_photo': self.create_test_image(),
            'selfie_photo': self.create_test_image(),
        })
        
        # Should be rejected (duplicate)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already registered', str(response2.data).lower())
    
    def test_phone_number_unicode_bypass(self):
        """Test phone number rejects unicode characters"""
        unicode_phones = [
            '+１２３４５６７８９０',  # Full-width digits
            '+1234５６７８90',  # Mixed
            '\u200e+1234567890',  # Zero-width character
        ]
        
        for phone in unicode_phones:
            response = self.client.post(self.send_otp_url, {'phone_number': phone})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('ASCII', str(response.data))
    
    def test_data_leakage_in_errors(self):
        """Test error messages don't leak sensitive data"""
        # Try to send OTP to phone verified by another user
        PhoneVerification.objects.create(
            user=self.other_user,
            phone_number='+9876543210',
            phone_number_hash='test_hash_123',
            is_verified=True
        )
        
        response = self.client.post(self.send_otp_url, {'phone_number': '+9876543210'})
        
        # Error should NOT reveal it's verified by another account
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('another account', str(response.data).lower())
        self.assertIn('not available', str(response.data).lower())


# =============================================================================
# FUNCTIONAL TESTS - Phone Verification
# =============================================================================

class PhoneVerificationFunctionalTests(BaseVerificationTest):
    """Functional tests for phone verification endpoints"""
    
    def test_send_otp_success(self):
        """Test successful OTP sending"""
        response = self.client.post(self.send_otp_url, {
            'phone_number': '+1234567890'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('OTP sent successfully', response.data['message'])
        self.assertEqual(response.data['expires_in'], 300)
        
        # Verify phone verification created
        self.assertTrue(PhoneVerification.objects.filter(user=self.user).exists())
    
    def test_send_otp_invalid_phone_format(self):
        """Test OTP sending with invalid phone formats"""
        invalid_phones = [
            '1234567890',  # Missing +
            '+12',  # Too short
            '+123456789012345678',  # Too long
            'invalid',
            '',
        ]
        
        for phone in invalid_phones:
            response = self.client.post(self.send_otp_url, {'phone_number': phone})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_verify_otp_success(self):
        """Test successful OTP verification"""
        # Mock OTP service to return success
        from common.services.otp import otp_service
        from unittest.mock import patch
        
        # Send OTP
        self.client.post(self.send_otp_url, {'phone_number': '+1234567890'})
        
        # Verify with mocked success
        with patch.object(otp_service, 'verify_otp', return_value={'success': True, 'message': 'Valid'}):
            response = self.client.post(self.verify_otp_url, {
                'phone_number': '+1234567890',
                'otp': '123456'
            })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['verified'])
        
        # Verify phone marked as verified
        phone_verification = PhoneVerification.objects.get(user=self.user)
        self.assertTrue(phone_verification.is_verified)
        self.assertIsNotNone(phone_verification.verified_at)
    
    def test_verify_otp_invalid(self):
        """Test OTP verification with wrong code"""
        self.client.post(self.send_otp_url, {'phone_number': '+1234567890'})
        
        response = self.client.post(self.verify_otp_url, {
            'phone_number': '+1234567890',
            'otp': '999999'  # Wrong OTP
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_phone_status_not_verified(self):
        """Test phone status when not verified"""
        response = self.client.get(self.phone_status_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_verified'])
        self.assertIsNone(response.data['phone_number'])
        self.assertIsNone(response.data['verified_at'])
    
    def test_phone_status_verified(self):
        """Test phone status when verified"""
        PhoneVerification.objects.create(
            user=self.user,
            phone_number='+1234567890',
            phone_number_hash='hash123',
            is_verified=True
        )
        
        response = self.client.get(self.phone_status_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_verified'])
        # Phone should be masked
        self.assertIn('****', response.data['phone_number'])


# =============================================================================
# FUNCTIONAL TESTS - Seller Verification
# =============================================================================

class SellerVerificationFunctionalTests(BaseVerificationTest):
    """Functional tests for seller verification endpoints"""
    
    def test_submit_verification_success(self):
        """Test successful verification submission"""
        response = self.client.post(self.submit_seller_url, {
            'national_id': 'ABC123XYZ',
            'date_of_birth': '1990-05-15',
            'billing_address': '123 Main St, New York, NY 10001',
            'id_front_photo': self.create_test_image('front.jpg'),
            'id_back_photo': self.create_test_image('back.jpg'),
            'selfie_photo': self.create_test_image('selfie.jpg'),
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'PENDING')
        
        # Verify seller verification created
        verification = SellerVerification.objects.get(user=self.user)
        self.assertEqual(verification.status, 'PENDING')
        # National ID should be encrypted
        self.assertIsNotNone(verification.national_id_encrypted)
        # Should have decryption method
        self.assertEqual(verification.national_id_decrypted, 'ABC123XYZ')
    
    def test_submit_verification_duplicate(self):
        """Test cannot submit verification twice"""
        data = {
            'national_id': 'TEST123',
            'date_of_birth': '1990-01-01',
            'billing_address': 'Test',
            'id_front_photo': self.create_test_image(),
            'id_back_photo': self.create_test_image(),
            'selfie_photo': self.create_test_image(),
        }
        
        # First submission
        response1 = self.client.post(self.submit_seller_url, data)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Second submission should fail
        response2 = self.client.post(self.submit_seller_url, {
            **data,
            'id_front_photo': self.create_test_image(),
            'id_back_photo': self.create_test_image(),
            'selfie_photo': self.create_test_image(),
        })
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_submit_verification_invalid_national_id(self):
        """Test validation of national ID"""
        invalid_ids = [
            'ABC',  # Too short
            'A' * 25,  # Too long
            'ABC@#$',  # Invalid characters
        ]
        
        for national_id in invalid_ids:
            response = self.client.post(self.submit_seller_url, {
                'national_id': national_id,
                'date_of_birth': '1990-01-01',
                'billing_address': 'Test',
                'id_front_photo': self.create_test_image(),
                'id_back_photo': self.create_test_image(),
                'selfie_photo': self.create_test_image(),
            })
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_seller_status_not_submitted(self):
        """Test seller status when not submitted"""
        response = self.client.get(self.seller_status_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_seller_status_pending(self):
        """Test seller status when pending"""
        SellerVerification.objects.create(
            user=self.user,
            national_id_encrypted='encrypted',
            national_id_hash='hash123',
            date_of_birth='1990-01-01',
            billing_address='Test',
            status='PENDING'
        )
        
        response = self.client.get(self.seller_status_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'PENDING')
        self.assertFalse(response.data['is_verified'])
    
    def test_can_create_offers_not_verified(self):
        """Test can_create_offers when not verified"""
        response = self.client.get(self.can_create_offers_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['can_create_offers'])
        self.assertIsNotNone(response.data['reason'])
    
    def test_can_create_offers_approved(self):
        """Test can_create_offers when approved"""
        SellerVerification.objects.create(
            user=self.user,
            national_id_encrypted='encrypted',
            national_id_hash='hash123',
            date_of_birth='1990-01-01',
            billing_address='Test',
            status='APPROVED'
        )
        
        response = self.client.get(self.can_create_offers_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['can_create_offers'])
        self.assertIsNone(response.data['reason'])


# =============================================================================
# FUNCTIONAL TESTS - Admin Endpoints
# =============================================================================

class AdminEndpointTests(BaseVerificationTest):
    """Tests for admin-only endpoints"""
    
    def test_pending_verifications_list(self):
        """Test listing pending verifications"""
        # Create some verifications
        SellerVerification.objects.create(
            user=self.user,
            national_id_encrypted='enc1',
            national_id_hash='hash1',
            date_of_birth='1990-01-01',
            billing_address='Test',
            status='PENDING'
        )
        
        SellerVerification.objects.create(
            user=self.other_user,
            national_id_encrypted='enc2',
            national_id_hash='hash2',
            date_of_birth='1990-01-01',
            billing_address='Test',
            status='APPROVED'  # Should not appear
        )
        
        response = self.admin_client.get(self.admin_pending_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only pending
        self.assertEqual(response.data[0]['status'], 'PENDING')
    
    def test_approve_verification_success(self):
        """Test approving a verification"""
        verification = SellerVerification.objects.create(
            user=self.user,
            national_id_encrypted='encrypted',
            national_id_hash='hash123',
            date_of_birth='1990-01-01',
            billing_address='Test',
            status='PENDING'
        )
        
        url = f'/api/verification/admin/approve/{verification.id}/'
        response = self.admin_client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify status changed
        verification.refresh_from_db()
        self.assertEqual(verification.status, 'APPROVED')
        self.assertEqual(verification.reviewed_by, self.admin_user)
        self.assertIsNotNone(verification.reviewed_at)
        
        # Verify audit log created
        self.assertTrue(
            VerificationAuditLog.objects.filter(
                user=self.user,
                action='SELLER_APPROVED',
                performed_by=self.admin_user
            ).exists()
        )
    
    def test_reject_verification_success(self):
        """Test rejecting a verification"""
        verification = SellerVerification.objects.create(
            user=self.user,
            national_id_encrypted='encrypted',
            national_id_hash='hash123',
            date_of_birth='1990-01-01',
            billing_address='Test',
            status='PENDING'
        )
        
        url = f'/api/verification/admin/reject/{verification.id}/'
        response = self.admin_client.post(url, {'reason': 'Documents not clear'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify status changed
        verification.refresh_from_db()
        self.assertEqual(verification.status, 'REJECTED')
        self.assertEqual(verification.rejection_reason, 'Documents not clear')
        
        # Verify audit log
        self.assertTrue(
            VerificationAuditLog.objects.filter(
                user=self.user,
                action='SELLER_REJECTED'
            ).exists()
        )
    
    def test_reject_without_reason_fails(self):
        """Test rejection requires reason"""
        verification = SellerVerification.objects.create(
            user=self.user,
            national_id_encrypted='encrypted',
            national_id_hash='hash123',
            date_of_birth='1990-01-01',
            billing_address='Test',
            status='PENDING'
        )
        
        url = f'/api/verification/admin/reject/{verification.id}/'
        response = self.admin_client.post(url, {})  # No reason
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class IntegrationTests(BaseVerificationTest):
    """End-to-end integration tests"""
    
    def test_complete_verification_flow(self):
        """Test complete flow: OTP → Verify → Submit KYC → Approve"""
        from unittest.mock import patch
        from common.services.otp import otp_service
        
        # Step 1: Send OTP
        response = self.client.post(self.send_otp_url, {'phone_number': '+1234567890'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Step 2: Verify OTP
        with patch.object(otp_service, 'verify_otp', return_value={'success': True, 'message': 'Valid'}):
            response = self.client.post(self.verify_otp_url, {
                'phone_number': '+1234567890',
                'otp': '123456'
            })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Step 3: Submit KYC
        response = self.client.post(self.submit_seller_url, {
            'national_id': 'FLOW123TEST',
            'date_of_birth': '1990-01-01',
            'billing_address': 'Integration Test Address',
            'id_front_photo': self.create_test_image(),
            'id_back_photo': self.create_test_image(),
            'selfie_photo': self.create_test_image(),
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 4: Admin approves
        verification = SellerVerification.objects.get(user=self.user)
        url = f'/api/verification/admin/approve/{verification.id}/'
        response = self.admin_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Step 5: Check can create offers
        response = self.client.get(self.can_create_offers_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['can_create_offers'])
    
    def test_rejection_flow(self):
        """Test rejection and handling"""
        # Submit verification
        self.client.post(self.submit_seller_url, {
            'national_id': 'REJECT123',
            'date_of_birth': '1990-01-01',
            'billing_address': 'Test',
            'id_front_photo': self.create_test_image(),
            'id_back_photo': self.create_test_image(),
            'selfie_photo': self.create_test_image(),
        })
        
        # Admin rejects
        verification = SellerVerification.objects.get(user=self.user)
        url = f'/api/verification/admin/reject/{verification.id}/'
        self.admin_client.post(url, {'reason': 'Please resubmit with clearer photos'})
        
        # Check status
        response = self.client.get(self.seller_status_url)
        self.assertEqual(response.data['status'], 'REJECTED')
        self.assertIn('clearer photos', response.data['rejection_reason'])
        
        # User cannot create offers
        response = self.client.get(self.can_create_offers_url)
        self.assertFalse(response.data['can_create_offers'])


print("✅ All test classes defined successfully")
