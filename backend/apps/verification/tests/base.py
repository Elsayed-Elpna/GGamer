"""
Base test classes and fixtures for verification tests.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.verification.models import PhoneVerification, SellerVerification
from common.services.encryption import encryption_service
from common.services.otp import otp_service
from io import BytesIO
from PIL import Image
import tempfile

User = get_user_model()


class BaseVerificationTestCase(TestCase):
    """Base test case with common setup for verification tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        
        # Create regular user
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='TestPass123!'
        )
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='AdminPass123!',
            is_staff=True,
            is_superuser=True
        )
        
        # Create support user
        self.support_user = User.objects.create_user(
            email='support@example.com',
            password='SupportPass123!',
            is_staff=True
        )
        
        # Create another regular user for cross-user tests
        self.other_user = User.objects.create_user(
            email='otheruser@example.com',
            password='OtherPass123!'
        )
    
    def authenticate(self, user=None):
        """Authenticate a user for API requests."""
        if user is None:
            user = self.user
        self.client.force_authenticate(user=user)
    
    def create_phone_verification(self, user=None, phone_number='+201012345678', verified=False):
        """Create a phone verification record."""
        if user is None:
            user = self.user
        
        phone_verification = PhoneVerification.objects.create(
            user=user,
            phone_number=phone_number,
            phone_number_hash=encryption_service.hash_national_id(phone_number),
            is_verified=verified
        )
        
        if verified:
            from django.utils import timezone
            phone_verification.verified_at = timezone.now()
            phone_verification.save()
        
        return phone_verification
    
    def create_seller_verification(self, user=None, status='PENDING', national_id='12345678901234'):
        """Create a seller verification record."""
        if user is None:
            user = self.user
        
        # Create test images
        id_front = self.create_test_image()
        id_back = self.create_test_image()
        selfie = self.create_test_image()
        
        seller_verification = SellerVerification.objects.create(
            user=user,
            national_id=national_id,
            national_id_hash=encryption_service.hash_national_id(national_id),
            date_of_birth='1990-01-01',
            billing_address='123 Test St, Cairo, Egypt',
            id_front_photo=id_front,
            id_back_photo=id_back,
            selfie_photo=selfie,
            status=status
        )
        
        return seller_verification
    
    def create_test_image(self, name='test.jpg', size=(100, 100), color='red'):
        """Create a test image file."""
        file = BytesIO()
        image = Image.new('RGB', size, color)
        image.save(file, 'JPEG')
        file.name = name
        file.seek(0)
        return file
    
    def get_valid_otp(self, phone_number):
        """Get a valid OTP for testing."""
        # Generate OTP
        otp_code = otp_service.generate_otp(phone_number)
        return otp_code
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up any uploaded files
        for verification in SellerVerification.objects.all():
            if verification.id_front_photo:
                verification.id_front_photo.delete()
            if verification.id_back_photo:
                verification.id_back_photo.delete()
            if verification.selfie_photo:
                verification.selfie_photo.delete()
        
        super().tearDown()


class APIEndpointTestMixin:
    """Mixin for testing API endpoints with common assertions."""
    
    def assert_response_success(self, response, status_code=200):
        """Assert response is successful."""
        self.assertEqual(response.status_code, status_code)
    
    def assert_response_error(self, response, status_code=400):
        """Assert response is an error."""
        self.assertEqual(response.status_code, status_code)
    
    def assert_requires_authentication(self, url, method='get'):
        """Assert endpoint requires authentication."""
        self.client.force_authenticate(user=None)
        
        if method == 'get':
            response = self.client.get(url)
        elif method == 'post':
            response = self.client.post(url, {})
        elif method == 'put':
            response = self.client.put(url, {})
        elif method == 'delete':
            response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 401)
    
    def assert_requires_admin(self, url, method='get', data=None):
        """Assert endpoint requires admin permissions."""
        self.authenticate(self.user)  # Regular user
        
        if method == 'get':
            response = self.client.get(url)
        elif method == 'post':
            response = self.client.post(url, data or {})
        
        self.assertEqual(response.status_code, 403)
    
    def assert_field_required(self, response, field_name):
        """Assert a field is required in the response errors."""
        self.assertIn(field_name, response.data)
        self.assertTrue(
            any('required' in str(error).lower() for error in response.data[field_name])
        )
    
    def assert_field_invalid(self, response, field_name):
        """Assert a field is invalid in the response errors."""
        self.assertIn(field_name, response.data)
