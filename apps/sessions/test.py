
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIClient

from contextlib import nullcontext
from unittest.mock import Mock

class MissionStartTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = SimpleNamespace(
            id=1,
            is_authenticated=True,
        )
        self.client.force_authenticate(user=self.user)

        self.mission = SimpleNamespace(
            id=1,
            duration_seconds=60,
        )

    def test_missing_mission_id(self):
        response = self.client.post(
            "/mission-sessions",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_mission_id(self):
        invalid_values = [-1, 0, "abc", True, 1.5]

        for value in invalid_values:
            with self.subTest(value=value):
                response = self.client.post(
                    "/mission-sessions",
                    {"missionId": value},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)

    @patch("apps.sessions.views.actions.Mission.objects.filter")
    def test_mission_not_found(self, mock_filter):
        mock_filter.return_value.first.return_value = None

        response = self.client.post(
            "/mission-sessions",
            {"missionId": 999},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        mock_filter.assert_called_once_with(
            id=999,
            is_active=True,
        )

    @patch("apps.sessions.views.actions.MissionSession.objects.create")
    @patch("apps.sessions.views.actions.Mission.objects.filter")
    def test_start_mission(self, mock_filter, mock_create):
        mock_filter.return_value.first.return_value = self.mission

        started_at = "2026-11-07T19:50:00+09:00"

        mock_create.return_value = SimpleNamespace(
            id=101,
            status="IN_PROGRESS",
            started_at=datetime.fromisoformat(started_at),
        )

        response = self.client.post(
            "/mission-sessions",
            {"missionId": 1},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "sessionId": 101,
                "missionId": 1,
                "status": "IN_PROGRESS",
                "durationSeconds": 60,
                "startedAt": started_at,
            },
        )

        mock_create.assert_called_once()
        self.assertEqual(
            mock_create.call_args.kwargs["user"],
            self.user,
        )


class MissionCompleteTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = SimpleNamespace(
            id=1,
            is_authenticated=True,
        )

        self.client.force_authenticate(user=self.user)

    def test_invalid_session_id(self):
        invalid_values = ["abc", "0", "-1", "1.5"]

        for session_id in invalid_values:
            with self.subTest(session_id=session_id):
                response = self.client.post(
                    f"/mission-sessions/{session_id}/complete",
                    format="json",
                )

                self.assertEqual(response.status_code, 400)

    @patch("apps.sessions.views.actions.transaction.atomic")
    @patch("apps.sessions.views.actions.MissionSession.objects.select_for_update")
    def test_session_not_found(self, mock_select, mock_atomic):
        mock_atomic.return_value = nullcontext()
        mock_select.return_value.filter.return_value.first.return_value = None

        response = self.client.post(
            "/mission-sessions/999/complete",
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        mock_select.return_value.filter.assert_called_once_with(
            id=999,
            user=self.user,
        )

    @patch("apps.sessions.views.actions.transaction.atomic")
    @patch("apps.sessions.views.actions.MissionSession.objects.select_for_update")
    def test_already_finished_session(self, mock_select, mock_atomic):
        mock_atomic.return_value = nullcontext()

        for session_status in ("COMPLETED", "CANCELLED"):
            with self.subTest(status=session_status):
                session = SimpleNamespace(
                    id=101,
                    status=session_status,
                )

                mock_select.return_value.filter.return_value.first.return_value = session

                response = self.client.post(
                    "/mission-sessions/101/complete",
                    format="json",
                )

                self.assertEqual(response.status_code, 409)

    @patch("apps.sessions.views.actions.transaction.atomic")
    @patch("apps.sessions.views.actions.MissionSession.objects.filter")
    @patch("apps.sessions.views.actions.MissionSession.objects.select_for_update")
    def test_complete_mission(
        self,
        mock_select,
        mock_filter,
        mock_atomic,
    ):
        mock_atomic.return_value = nullcontext()

        session = SimpleNamespace(
            id=101,
            mission_id=1,
            status="IN_PROGRESS",
            completed_at=None,
            save=Mock(),
        )

        mock_select.return_value.filter.return_value.first.return_value = session
        mock_filter.return_value.count.return_value = 3

        response = self.client.post(
            "/mission-sessions/101/complete",
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        result = response.json()

        self.assertEqual(
            set(result.keys()),
            {
                "sessionId",
                "missionId",
                "status",
                "completedAt",
                "todayCompletedCount",
            },
        )
        self.assertEqual(result["sessionId"], 101)
        self.assertEqual(result["missionId"], 1)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["todayCompletedCount"], 3)
        self.assertIsInstance(result["completedAt"], str)

        session.save.assert_called_once_with(
            update_fields=["status", "completed_at"]
        )

        filter_arguments = mock_filter.call_args.kwargs

        self.assertEqual(filter_arguments["user"], self.user)
        self.assertEqual(
            filter_arguments["status"],
            "COMPLETED",
        )
        self.assertIn("completed_at__date", filter_arguments)


class MissionCancelTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = SimpleNamespace(
            id=1,
            is_authenticated=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_invalid_session_id(self):
        for session_id in ("abc", "0", "-1", "1.5"):
            with self.subTest(session_id=session_id):
                response = self.client.post(
                    f"/mission-sessions/{session_id}/cancel",
                    format="json",
                )
                self.assertEqual(response.status_code, 400)

    @patch("apps.sessions.views.actions.transaction.atomic")
    @patch("apps.sessions.views.actions.MissionSession.objects.select_for_update")
    def test_session_not_found(self, mock_select, mock_atomic):
        mock_atomic.return_value = nullcontext()
        mock_select.return_value.filter.return_value.first.return_value = None

        response = self.client.post(
            "/mission-sessions/999/cancel",
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        mock_select.return_value.filter.assert_called_once_with(
            id=999,
            user=self.user,
        )

    @patch("apps.sessions.views.actions.transaction.atomic")
    @patch("apps.sessions.views.actions.MissionSession.objects.select_for_update")
    def test_already_finished_session(self, mock_select, mock_atomic):
        mock_atomic.return_value = nullcontext()

        for session_status in ("COMPLETED", "CANCELLED"):
            with self.subTest(status=session_status):
                session = SimpleNamespace(
                    id=101,
                    status=session_status,
                )
                mock_select.return_value.filter.return_value.first.return_value = session

                response = self.client.post(
                    "/mission-sessions/101/cancel",
                    format="json",
                )

                self.assertEqual(response.status_code, 409)

    @patch("apps.sessions.views.actions.transaction.atomic")
    @patch("apps.sessions.views.actions.MissionSession.objects.select_for_update")
    def test_cancel_mission(self, mock_select, mock_atomic):
        mock_atomic.return_value = nullcontext()

        session = SimpleNamespace(
            id=101,
            mission_id=1,
            status="IN_PROGRESS",
            cancelled_at=None,
            save=Mock(),
        )
        mock_select.return_value.filter.return_value.first.return_value = session

        response = self.client.post(
            "/mission-sessions/101/cancel",
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertEqual(
            set(result.keys()),
            {
                "sessionId",
                "missionId",
                "status",
                "cancelledAt",
            },
        )
        self.assertEqual(result["sessionId"], 101)
        self.assertEqual(result["missionId"], 1)
        self.assertEqual(result["status"], "CANCELLED")
        self.assertIsInstance(result["cancelledAt"], str)

        session.save.assert_called_once_with(
            update_fields=["status", "cancelled_at"]
        )
