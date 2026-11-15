
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIClient


class MissionApiTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

        self.mission = SimpleNamespace(
            id=1,
            title="물 한 잔 마시기",
            description="물을 천천히 마셔보세요.",
            category="INDOOR",
            duration_seconds=60,
            image_url="/images/water.png",
        )

    @patch("apps.missions.views.Mission.objects.filter")
    def test_mission_list(self, mock_filter):
        mock_filter.return_value.order_by.return_value = [
            self.mission
        ]

        response = self.client.get(
            "/missions",
            {"category": "INDOOR"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "missions": [
                    {
                        "missionId": 1,
                        "title": "물 한 잔 마시기",
                        "description": "물을 천천히 마셔보세요.",
                        "category": "INDOOR",
                        "durationSeconds": 60,
                    }
                ]
            },
        )

        mock_filter.assert_called_once_with(
            category="INDOOR",
            is_active=True,
        )

    @patch("apps.missions.views.Mission.objects.filter")
    def test_random_mission(self, mock_filter):
        mock_filter.return_value.order_by.return_value.first.return_value = (
            self.mission
        )

        response = self.client.get(
            "/missions/random",
            {"category": "INDOOR"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "missionId": 1,
                "title": "물 한 잔 마시기",
                "description": "물을 천천히 마셔보세요.",
                "category": "INDOOR",
                "durationSeconds": 60,
                "imageUrl": "/images/water.png",
            },
        )

    def test_invalid_category(self):
        for url in ("/missions", "/missions/random"):
            for category in (None, "INVALID", ""):
                with self.subTest(url=url, category=category):
                    parameters = (
                        {}
                        if category is None
                        else {"category": category}
                    )

                    response = self.client.get(
                        url,
                        parameters,
                    )

                    self.assertEqual(response.status_code, 400)

    @patch("apps.missions.views.Mission.objects.filter")
    def test_empty_mission_list(self, mock_filter):
        mock_filter.return_value.order_by.return_value = []

        response = self.client.get(
            "/missions",
            {"category": "OUTDOOR"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"missions": []})

    @patch("apps.missions.views.Mission.objects.filter")
    def test_random_mission_not_found(self, mock_filter):
        mock_filter.return_value.order_by.return_value.first.return_value = (
            None
        )

        response = self.client.get(
            "/missions/random",
            {"category": "OUTDOOR"},
        )

        self.assertEqual(response.status_code, 404)
