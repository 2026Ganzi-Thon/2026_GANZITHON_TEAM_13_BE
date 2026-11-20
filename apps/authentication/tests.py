
from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.auth import get_user_model


class GuestAuthenticationTests(APITestCase):

    def test_guest_creation(self):
        response = self.client.post("/auth/guest")

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertIn("userId", response.data)
        self.assertIn("accessToken", response.data)
        self.assertIn("refreshToken", response.data)

        User = get_user_model()

        user = User.objects.get(
            id=response.data["userId"]
        )

        self.assertFalse(user.has_usable_password())

    def test_token_refresh(self):
        guest_response = self.client.post("/auth/guest")

        refresh_token = guest_response.data["refreshToken"]

        response = self.client.post(
            "/auth/refresh",
            {"refresh": refresh_token},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn("access", response.data)

    def test_unauthenticated_request(self):
        response = self.client.get(
            "/rest/records/today"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_request(self):
        guest_response = self.client.post("/auth/guest")

        access_token = guest_response.data["accessToken"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.get(
            "/rest/records/today"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            {"record": None},
        )
