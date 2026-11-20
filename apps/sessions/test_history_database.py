from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.missions.models import Mission
from apps.sessions.models import MissionSession


class MissionHistoryDatabaseTests(TestCase):
    """Exercise real ORM queries, foreign keys and deletion in a test database."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="history-owner")
        cls.other = get_user_model().objects.create_user(username="other-owner")
        cls.mission = Mission.objects.create(
            title="Test mission", description="Test", category="INDOOR",
            duration_seconds=60,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def record(self, user=None, **fields):
        return MissionSession.objects.create(
            user=user or self.user, mission=self.mission,
            **{"status": "IN_PROGRESS", **fields},
        )

    def test_list_isolates_users_and_orders_equal_timestamps(self):
        first = self.record()
        second = self.record(started_at=first.started_at)
        self.record(user=self.other)
        response = self.client.get("/mission-sessions")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["id"] for row in response.json()["records"]],
            [second.id, first.id],
        )

    def test_delete_preserves_other_user_and_mission(self):
        for status in MissionSession.Status.values:
            self.record(status=status)
        other_record = self.record(user=self.other)
        response = self.client.delete("/mission-sessions")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertFalse(MissionSession.objects.filter(user=self.user).exists())
        self.assertTrue(MissionSession.objects.filter(pk=other_record.pk).exists())
        self.assertTrue(Mission.objects.filter(pk=self.mission.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_empty_list_and_repeated_delete(self):
        other_record = self.record(user=self.other)
        for _ in range(2):
            response = self.client.get("/mission-sessions")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"records": []})
            self.assertEqual(self.client.delete("/mission-sessions").status_code, 204)
        self.assertTrue(MissionSession.objects.filter(pk=other_record.pk).exists())

    def test_unauthenticated_requests_preserve_records(self):
        record = self.record()
        self.client = APIClient()
        for method in ("get", "delete"):
            response = getattr(self.client, method)("/mission-sessions")
            self.assertEqual(response.status_code, 401)
        self.assertTrue(MissionSession.objects.filter(pk=record.pk).exists())

    def test_status_and_calendar_filters_use_real_queries(self):
        start = datetime(2026, 11, 16, tzinfo=ZoneInfo("Asia/Seoul"))
        end = start + timedelta(days=7)
        for timestamp in (start - timedelta(microseconds=1), end):
            self.record(status="COMPLETED", started_at=timestamp)
        expected = self.record(status="COMPLETED", started_at=start)
        self.record(started_at=start)
        self.record(user=self.other, status="COMPLETED", started_at=start)
        with patch("apps.sessions.views.history.timezone.now", return_value=start):
            response = self.client.get(
                "/mission-sessions", {"status": "COMPLETED", "period": "week"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["id"] for r in response.json()["records"]], [expected.id])

    def test_invalid_filters_do_not_delete_or_change_records(self):
        record = self.record()
        for params in ({"status": "INVALID"}, {"period": "year"}):
            self.assertEqual(self.client.get("/mission-sessions", params).status_code, 400)
        record.refresh_from_db()
        self.assertEqual(record.status, "IN_PROGRESS")

    def test_mission_lifecycle_remains_compatible_with_history(self):
        response = self.client.get("/missions", {"category": "INDOOR"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["missions"][0]["missionId"], self.mission.pk)
        self.assertEqual(
            self.client.get("/missions/random", {"category": "INDOOR"}).status_code, 200,
        )
        for action, expected in (("complete", "COMPLETED"), ("cancel", "CANCELLED")):
            response = self.client.post(
                "/mission-sessions", {"missionId": self.mission.pk}, format="json",
            )
            self.assertEqual(response.status_code, 201)
            session_id = response.json()["sessionId"]
            response = self.client.post(f"/mission-sessions/{session_id}/{action}")
            self.assertEqual(response.status_code, 200)
            if action == "complete":
                self.assertEqual(response.json()["todayCompletedCount"], 1)
            rows = self.client.get("/mission-sessions").json()["records"]
            self.assertEqual(next(r["status"] for r in rows if r["id"] == session_id), expected)
        self.assertEqual(self.client.delete("/mission-sessions").status_code, 204)
        self.assertEqual(self.client.get("/mission-sessions").json(), {"records": []})
