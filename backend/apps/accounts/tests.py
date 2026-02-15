from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from apps.accounts.models import User


class TestAccountsAPI(APITestCase):

    def setUp(self):

        # URLs
        self.register_url = reverse("accounts:register")
        self.login_url = reverse("jwt_login")
        self.me_url = reverse("accounts:me")

        # Test User
        self.user_data = {
            "email": "user@test.com",
            "password": "StrongPass123!"
        }

    # ======================================================
    # REGISTER TESTS
    # ======================================================

    def test_register_success(self):

        response = self.client.post(self.register_url, self.user_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="user@test.com").exists())

    def test_register_duplicate_email(self):

        self.client.post(self.register_url, self.user_data)

        response = self.client.post(self.register_url, self.user_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_password(self):

        response = self.client.post(self.register_url, {
            "email": "nopass@test.com"
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ======================================================
    # JWT LOGIN TESTS
    # ======================================================

    def test_jwt_login_success(self):

        self.client.post(self.register_url, self.user_data)

        response = self.client.post(self.login_url, self.user_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_wrong_password(self):

        self.client.post(self.register_url, self.user_data)

        response = self.client.post(self.login_url, {
            "email": "user@test.com",
            "password": "WrongPassword123"
        })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_non_existing_user(self):

        response = self.client.post(self.login_url, {
            "email": "ghost@test.com",
            "password": "123456"
        })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ======================================================
    # PROTECTED ENDPOINT TESTS
    # ======================================================

    def test_me_endpoint_requires_auth(self):

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_with_token(self):

        # Register
        self.client.post(self.register_url, self.user_data)

        # Login
        login_response = self.client.post(self.login_url, self.user_data)
        token = login_response.data["access"]

        # Set Authorization Header
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "user@test.com")

    # ======================================================
    # SECURITY TESTS
    # ======================================================

    def test_banned_user_cannot_login(self):

        # Register user
        self.client.post(self.register_url, self.user_data)

        user = User.objects.get(email="user@test.com")
        user.is_banned = True
        user.save()

        response = self.client.post(self.login_url, self.user_data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
