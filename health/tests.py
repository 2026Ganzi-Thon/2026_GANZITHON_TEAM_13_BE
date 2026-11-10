from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIClient


class HealthCheckTests(SimpleTestCase):
    # SimpleTestCase forbids database queries and does not create a test DB.
    def setUp(self):
        self.client = APIClient()

    def test_health_is_public_json_and_does_not_require_database(self):
        self.assertEqual(reverse("health-check"), "/api/health/")
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response["Content-Type"], "application/json")

    def test_post_is_not_allowed(self):
        response = self.client.post("/api/health/", {}, format="json")
        self.assertEqual(response.status_code, 405)
