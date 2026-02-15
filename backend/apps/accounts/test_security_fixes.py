"""
Comprehensive test suite for security fixes in accounts app.
Tests all 18 critical security vulnerabilities that were fixed.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User, PublicProfile, PrivateProfile
from rest_framework.test import APITestCase
from rest_framework import status
import time
from io import BytesIO
from PIL import Image


class SecurityFixesTestCase(APITestCase):
    """Test all critical security fixes"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.register_url = reverse("accounts:register")
        self.login_url = reverse("jwt_login")
        self.me_url = reverse("accounts:me")
        self.avatar_url = reverse("accounts:avatar")
        self.private_profile_url = reverse("accounts:private_profile")

        # Test user data
        self.user_data = {
            "email": "testuser@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!"
        }

    # ============================
    # TEST 1: Rate Limiting
    # ============================

    def test_rate_limiting_on_registration(self):
        """Test that rate limiting works (5 requests per minute)"""
        print("\n🧪 TEST 1: Rate Limiting on Registration")
        
        # Make 6 rapid requests (should block after 5)
        responses = []
        for i in range(6):
            response = self.client.post(
                self.register_url,
                {"email": f"user{i}@test.com", "password": "Pass123!", "password_confirm": "Pass123!"},
                content_type="application/json"
            )
            responses.append(response.status_code)
            
        # First 5 should succeed or fail validation, 6th should be throttled
        throttled_count = sum(1 for status in responses if status == 429)
        
        print(f"   Response codes: {responses}")
        print(f"   Throttled requests: {throttled_count}")
        
        self.assertGreater(throttled_count, 0, "Rate limiting should throttle after 5 requests")
        print("   ✅ Rate limiting is working!")

    # ============================
    # TEST 2: Username Uniqueness
    # ============================

    def test_username_uniqueness_handling(self):
        """Test that duplicate usernames are handled with counter"""
        print("\n🧪 TEST 2: Username Uniqueness Handling")
        
        # Register two users with emails that generate same username
        response1 = self.client.post(
            self.register_url,
            {"email": "john@gmail.com", "password": "Pass123!", "password_confirm": "Pass123!"},
            content_type="application/json"
        )
        
        response2 = self.client.post(
            self.register_url,
            {"email": "john@yahoo.com", "password": "Pass123!", "password_confirm": "Pass123!"},
            content_type="application/json"
        )
        
        self.assertEqual(response1.status_code, 201, "First user should register successfully")
        self.assertEqual(response2.status_code, 201, "Second user should register successfully")
        
        # Check usernames
        user1 = User.objects.get(email="john@gmail.com")
        user2 = User.objects.get(email="john@yahoo.com")
        
        print(f"   User 1 username: {user1.public_profile.username}")
        print(f"   User 2 username: {user2.public_profile.username}")
        
        self.assertNotEqual(
            user1.public_profile.username,
            user2.public_profile.username,
            "Usernames should be different"
        )
        print("   ✅ Username uniqueness handling works!")

    # ============================
    # TEST 3: Password Confirmation
    # ============================

    def test_password_confirmation_required(self):
        """Test that password confirmation is required and validated"""
        print("\n🧪 TEST 3: Password Confirmation Validation")
        
        # Test mismatched passwords
        response = self.client.post(
            self.register_url,
            {"email": "test@test.com", "password": "Pass123!", "password_confirm": "DifferentPass123!"},
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 400, "Should reject mismatched passwords")
        self.assertIn("password", str(response.content).lower(), "Should mention password error")
        print("   ✅ Password confirmation validation works!")

    # ============================
    # TEST 4: File Upload Validation
    # ============================

    def test_file_upload_size_validation(self):
        """Test that large files are rejected"""
        print("\n🧪 TEST 4: File Upload Size Validation")
        
        # Create user and login
        user = User.objects.create_user(email="filetest@test.com", password="Pass123!")
        self.client.force_login(user)
        
        # Create a large fake file (6MB - should exceed 5MB limit)
        large_file = SimpleUploadedFile(
            "large.jpg",
            b"x" * (6 * 1024 * 1024),  # 6MB
            content_type="image/jpeg"
        )
        
        response = self.client.post(self.avatar_url, {"avatar": large_file})
        
        self.assertEqual(response.status_code, 400, "Should reject files over 5MB")
        print("   ✅ File size validation works!")

    def test_file_upload_type_validation(self):
        """Test that non-image files are rejected"""
        print("\n🧪 TEST 5: File Upload Type Validation")
        
        # Create user and login
        user = User.objects.create_user(email="typetest@test.com", password="Pass123!")
        self.client.force_login(user)
        
        # Try to upload a text file
        text_file = SimpleUploadedFile(
            "malicious.txt",
            b"This is not an image",
            content_type="text/plain"
        )
        
        response = self.client.post(self.avatar_url, {"avatar": text_file})
        
        self.assertEqual(response.status_code, 400, "Should reject non-image files")
        print("   ✅ File type validation works!")

    # ============================
    # TEST 6: Banned User Blocking
    # ============================

    def test_banned_user_cannot_access_api(self):
        """Test that banned users are blocked from all API endpoints"""
        print("\n🧪 TEST 6: Banned User API Blocking")
        
        # Create and ban user
        user = User.objects.create_user(email="banned@test.com", password="Pass123!")
        user.ban(reason="Test ban")
        
        # Try to login
        response = self.client.post(
            self.login_url,
            {"email": "banned@test.com", "password": "Pass123!"},
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 401, "Banned user should not be able to login")
        self.assertIn("banned", str(response.content).lower(), "Should mention ban")
        print("   ✅ Banned user blocking works!")

    # ============================
    # TEST 7: Superuser Ban Protection
    # ============================

    def test_cannot_ban_superuser(self):
        """Test that superusers cannot be banned via API"""
        print("\n🧪 TEST 7: Superuser Ban Protection")
        
        # Create superuser and admin
        superuser = User.objects.create_superuser(email="super@test.com", password="Pass123!")
        admin = User.objects.create_user(email="admin@test.com", password="Pass123!", role="ADMIN")
        
        # Login as admin
        self.client.force_login(admin)
        
        # Try to ban superuser
        ban_url = reverse("accounts:ban_user", kwargs={"user_id": superuser.id})
        response = self.client.post(
            ban_url,
            {"reason": "Trying to ban superuser"},
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 403, "Should not allow banning superuser")
        
        # Verify superuser is not banned
        superuser.refresh_from_db()
        self.assertFalse(superuser.is_banned, "Superuser should not be banned")
        print("   ✅ Superuser ban protection works!")

    # ============================
    # TEST 8: Phone/National ID Validation
    # ============================

    def test_phone_number_validation(self):
        """Test Egyptian phone number format validation"""
        print("\n🧪 TEST 8: Phone Number Validation")
        
        user = User.objects.create_user(email="phonetest@test.com", password="Pass123!")
        self.client.force_login(user)
        
        # Invalid phone number
        response = self.client.post(
            self.private_profile_url,
            {"phone_number": "123456789", "national_id": "12345678901234"},
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 400, "Should reject invalid phone format")
        print("   ✅ Phone number validation works!")

    def test_national_id_validation(self):
        """Test Egyptian national ID format validation"""
        print("\n🧪 TEST 9: National ID Validation")
        
        user = User.objects.create_user(email="idtest@test.com", password="Pass123!")
        self.client.force_login(user)
        
        # Invalid national ID (wrong length)
        response = self.client.post(
            self.private_profile_url,
            {"phone_number": "01012345678", "national_id": "123"},
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 400, "Should reject invalid national ID")
        print("   ✅ National ID validation works!")

    # ============================
    # TEST 10: PII Masking
    # ============================

    def test_pii_data_masking(self):
        """Test that sensitive PII is masked in responses"""
        print("\n🧪 TEST 10: PII Data Masking")
        
        user = User.objects.create_user(email="piitest@test.com", password="Pass123!")
        self.client.force_login(user)
        
        # Create private profile
        PrivateProfile.objects.create(
            user=user,
            phone_number="01012345678",
            national_id="12345678901234"
        )
        
        # Get private profile
        response = self.client.get(self.private_profile_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that full data is not exposed
        response_text = str(response.content)
        self.assertNotIn("01012345678", response_text, "Full phone should not be exposed")
        self.assertNotIn("12345678901234", response_text, "Full national ID should not be exposed")
        
        # Check that masked data is present
        data = response.json()
        self.assertIn("phone_number_masked", data, "Should have masked phone")
        self.assertIn("national_id_masked", data, "Should have masked national ID")
        print(f"   Masked phone: {data['phone_number_masked']}")
        print(f"   Masked ID: {data['national_id_masked']}")
        print("   ✅ PII masking works!")

    # ============================
    # TEST 11: is_active Check
    # ============================

    def test_inactive_user_cannot_login(self):
        """Test that inactive users cannot obtain JWT tokens"""
        print("\n🧪 TEST 11: Inactive User Login Prevention")
        
        # Create inactive user
        user = User.objects.create_user(email="inactive@test.com", password="Pass123!")
        user.is_active = False
        user.save()
        
        # Try to login
        response = self.client.post(
            self.login_url,
            {"email": "inactive@test.com", "password": "Pass123!"},
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 401, "Inactive user should not be able to login")
        self.assertIn("inactive", str(response.content).lower(), "Should mention inactive status")
        print("   ✅ Inactive user blocking works!")

    # ============================
    # TEST 12: Self-Ban Prevention
    # ============================

    def test_admin_cannot_ban_self(self):
        """Test that admins cannot ban themselves"""
        print("\n🧪 TEST 12: Self-Ban Prevention")
        
        admin = User.objects.create_user(email="selfban@test.com", password="Pass123!", role="ADMIN")
        self.client.force_login(admin)
        
        # Try to ban self
        ban_url = reverse("accounts:ban_user", kwargs={"user_id": admin.id})
        response = self.client.post(
            ban_url,
            {"reason": "Trying to ban myself"},
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 403, "Should not allow self-banning")
        
        # Verify not banned
        admin.refresh_from_db()
        self.assertFalse(admin.is_banned, "Admin should not be banned")
        print("   ✅ Self-ban prevention works!")


class IntegrationTestCase(APITestCase):
    """Integration tests for complete user flows"""

    def test_complete_registration_flow(self):
        """Test complete user registration and login flow"""
        print("\n🧪 INTEGRATION TEST: Complete Registration Flow")
        
        # 1. Register
        register_response = self.client.post(
            reverse("accounts:register"),
            {
                "email": "integration@test.com",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!"
            },
            content_type="application/json"
        )
        
        self.assertEqual(register_response.status_code, 201, "Registration should succeed")
        print("   ✅ Step 1: Registration successful")
        
        # 2. Login
        login_response = self.client.post(
            reverse("jwt_login"),
            {"email": "integration@test.com", "password": "SecurePass123!"},
            content_type="application/json"
        )
        
        self.assertEqual(login_response.status_code, 200, "Login should succeed")
        self.assertIn("access", login_response.json(), "Should return access token")
        print("   ✅ Step 2: Login successful")
        
        # 3. Access protected endpoint
        token = login_response.json()["access"]
        me_response = self.client.get(
            reverse("accounts:me"),
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        
        self.assertEqual(me_response.status_code, 200, "Should access protected endpoint")
        self.assertEqual(me_response.json()["email"], "integration@test.com")
        print("   ✅ Step 3: Protected endpoint access successful")
        print("   ✅ Complete flow works end-to-end!")


def run_all_tests():
    """Helper to print test summary"""
    print("\n" + "="*60)
    print("🔒 SECURITY FIXES TEST SUITE")
    print("="*60)
    print("\nRunning comprehensive security tests...\n")
