from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import User


class AccountTests(APITestCase):

    def test_register(self):

        data = {
            "email": "test@test.com",
            "password": "StrongPass123!"
        }

        response = self.client.post("/api/accounts/register/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="test@test.com").exists())
