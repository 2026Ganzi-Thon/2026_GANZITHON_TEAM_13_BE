from datetime import datetime, timedelta, timezone as datetime_timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIClient


SEOUL = ZoneInfo("Asia/Seoul")


class MissionHistoryTests(SimpleTestCase):
    # ORM calls are mocked. These tests prohibit database access.
    def setUp(self):
        self.client = APIClient()
        self.user = SimpleNamespace(id=1, is_authenticated=True)
        self.client.force_authenticate(user=self.user)
        self.manager_patch = patch("apps.sessions.views.history.MissionSession.objects")
        self.manager = self.manager_patch.start()
        self.addCleanup(self.manager_patch.stop)
        self.records = self.manager.filter.return_value
        self.filtered_records = MagicMock(name="filtered_records")
        self.records.filter.return_value = self.filtered_records
        self.records.order_by.return_value = []

    def ordered_result(self, queryset, records):
        ordered = MagicMock(name="ordered_records", spec=["__iter__"])
        ordered.__iter__.return_value = records
        queryset.order_by.return_value = ordered
        return ordered

    def assert_ordered_and_evaluated(self, queryset, ordered):
        queryset.order_by.assert_called_once_with("-started_at", "-id")
        ordered.__iter__.assert_called_once_with()
        queryset.__iter__.assert_not_called()

    def record(self, record_id=1, started_at=None, **fields):
        values = {
            "id": record_id,
            "mission_id": 3,
            "status": "COMPLETED",
            "started_at": started_at or datetime(2026, 11, 16, 1, tzinfo=datetime_timezone.utc),
            "completed_at": datetime(2026, 11, 16, 1, 1, tzinfo=datetime_timezone.utc),
            "cancelled_at": None,
        }
        values.update(fields)
        return SimpleNamespace(**values)

    def test_default_list_and_seoul_serialization(self):
        self.records.order_by.return_value = [self.record()]
        response = self.client.get("/mission-sessions")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"records": [{
            "id": 1, "missionId": 3, "status": "COMPLETED",
            "startedAt": "2026-11-16T10:00:00+09:00",
            "completedAt": "2026-11-16T10:01:00+09:00",
            "cancelledAt": None,
        }]})
        self.manager.filter.assert_called_once_with(user=self.user)
        self.records.filter.assert_not_called()
        self.records.order_by.assert_called_once_with("-started_at", "-id")

    def test_nullable_timestamps_and_cancelled_timestamp(self):
        self.records.order_by.return_value = [self.record(
            status="CANCELLED", completed_at=None,
            cancelled_at=datetime(2026, 11, 16, 1, 2, tzinfo=datetime_timezone.utc),
        )]
        record = self.client.get("/mission-sessions").json()["records"][0]
        self.assertIsNone(record["completedAt"])
        self.assertEqual(record["cancelledAt"], "2026-11-16T10:02:00+09:00")

    def test_each_status_filter(self):
        for status in ("IN_PROGRESS", "COMPLETED", "CANCELLED"):
            with self.subTest(status=status):
                self.records.reset_mock()
                selected = MagicMock(name="status_records")
                self.records.filter.return_value = selected
                ordered = self.ordered_result(selected, [self.record(status=status)])
                response = self.client.get("/mission-sessions", {"status": status})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    [r["status"] for r in response.json()["records"]], [status],
                )
                self.manager.filter.assert_called_with(user=self.user)
                self.records.filter.assert_called_once_with(status=status)
                self.records.order_by.assert_not_called()
                self.records.__iter__.assert_not_called()
                self.assert_ordered_and_evaluated(selected, ordered)

    def test_all_period_has_no_date_filter(self):
        response = self.client.get("/mission-sessions", {"period": "all"})
        self.assertEqual(response.status_code, 200)
        self.records.filter.assert_not_called()

    def test_invalid_filters_do_not_query(self):
        for parameters in (
            {"status": "INVALID"}, {"status": "completed"}, {"status": ""},
            {"period": "year"}, {"period": "WEEK"}, {"period": ""},
        ):
            with self.subTest(parameters=parameters):
                response = self.client.get("/mission-sessions", parameters)
                self.assertEqual(response.status_code, 400)
        self.manager.filter.assert_not_called()

    def test_empty_list(self):
        response = self.client.get("/mission-sessions")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"records": []})

    def test_unauthenticated_requests_do_not_query(self):
        for user in (None, SimpleNamespace(is_authenticated=False)):
            client = APIClient()
            if user is not None:
                client.force_authenticate(user=user)
            for method in ("get", "delete"):
                with self.subTest(user=user, method=method):
                    response = getattr(client, method)("/mission-sessions")
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.json(), {"detail": "Authentication required."})
        self.manager.filter.assert_not_called()

    def test_user_scoped_list(self):
        other_user = SimpleNamespace(id=2, is_authenticated=True)
        first_records = MagicMock()
        second_records = MagicMock()
        first_records.order_by.return_value = [self.record(record_id=11)]
        second_records.order_by.return_value = [self.record(record_id=22)]
        self.manager.filter.side_effect = lambda *, user: (
            first_records if user is self.user else second_records
        )
        for user, expected_id in ((self.user, 11), (other_user, 22)):
            with self.subTest(user=user.id):
                self.client.force_authenticate(user=user)
                response = self.client.get("/mission-sessions")
                self.assertEqual(response.status_code, 200)
                self.assertEqual([r["id"] for r in response.json()["records"]], [expected_id])
                self.manager.filter.assert_called_with(user=user)

    def test_calendar_period_boundaries(self):
        cases = (
            # UTC Sunday is already Monday in Seoul.
            ("week", datetime(2026, 11, 15, 15, tzinfo=datetime_timezone.utc),
             datetime(2026, 11, 16, tzinfo=SEOUL), datetime(2026, 11, 23, tzinfo=SEOUL)),
            ("week", datetime(2026, 11, 22, 14, 59, 59, tzinfo=datetime_timezone.utc),
             datetime(2026, 11, 16, tzinfo=SEOUL), datetime(2026, 11, 23, tzinfo=SEOUL)),
            ("week", datetime(2026, 11, 22, 15, tzinfo=datetime_timezone.utc),
             datetime(2026, 11, 23, tzinfo=SEOUL), datetime(2026, 11, 30, tzinfo=SEOUL)),
            ("month", datetime(2026, 10, 31, 15, tzinfo=datetime_timezone.utc),
             datetime(2026, 11, 1, tzinfo=SEOUL), datetime(2026, 12, 1, tzinfo=SEOUL)),
            ("month", datetime(2026, 12, 15, tzinfo=SEOUL),
             datetime(2026, 12, 1, tzinfo=SEOUL), datetime(2027, 1, 1, tzinfo=SEOUL)),
            ("month", datetime(2028, 2, 29, tzinfo=SEOUL),
             datetime(2028, 2, 1, tzinfo=SEOUL), datetime(2028, 3, 1, tzinfo=SEOUL)),
        )
        for period, now, start, end in cases:
            with self.subTest(period=period, now=now):
                self.records.reset_mock()
                selected = MagicMock(name="period_records")
                self.records.filter.return_value = selected
                ordered = self.ordered_result(selected, [self.record(started_at=start)])
                # Boundaries must use Seoul even if another zone is active.
                with timezone.override("UTC"), patch(
                    "apps.sessions.views.history.timezone.now", return_value=now
                ):
                    response = self.client.get("/mission-sessions", {"period": period})
                self.assertEqual(response.status_code, 200)
                self.records.filter.assert_called_once_with(
                    started_at__gte=start, started_at__lt=end,
                )
                self.assertEqual(len(response.json()["records"]), 1)
                self.records.order_by.assert_not_called()
                self.records.__iter__.assert_not_called()
                self.assert_ordered_and_evaluated(selected, ordered)

    def test_period_includes_start_and_excludes_end(self):
        start = datetime(2026, 11, 16, tzinfo=SEOUL)
        end = datetime(2026, 11, 23, tzinfo=SEOUL)
        candidates = [self.record(record_id=i, started_at=timestamp) for i, timestamp in enumerate((
            start - timedelta(microseconds=1), start,
            end - timedelta(microseconds=1), end,
        ), start=1)]

        def apply_date_filter(**lookups):
            selected = MagicMock()
            selected.order_by.return_value = [r for r in reversed(candidates) if
                lookups["started_at__gte"] <= r.started_at < lookups["started_at__lt"]]
            return selected

        self.records.filter.side_effect = apply_date_filter
        with patch("apps.sessions.views.history.timezone.now", return_value=start):
            response = self.client.get("/mission-sessions", {"period": "week"})
        self.assertEqual([r["id"] for r in response.json()["records"]], [3, 2])

    def test_combined_status_and_period(self):
        now = datetime(2026, 11, 16, tzinfo=SEOUL)
        status_records = self.filtered_records
        period_records = MagicMock(name="period_records")
        status_records.filter.return_value = period_records
        ordered = self.ordered_result(period_records, [self.record(record_id=99)])
        with patch("apps.sessions.views.history.timezone.now", return_value=now):
            response = self.client.get("/mission-sessions", {"status": "COMPLETED", "period": "month"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["id"] for r in response.json()["records"]], [99])
        self.manager.filter.assert_called_once_with(user=self.user)
        self.records.filter.assert_called_once_with(status="COMPLETED")
        status_records.filter.assert_called_once_with(
            started_at__gte=datetime(2026, 11, 1, tzinfo=SEOUL),
            started_at__lt=datetime(2026, 12, 1, tzinfo=SEOUL),
        )
        for intermediate in (self.records, status_records):
            intermediate.order_by.assert_not_called()
            intermediate.__iter__.assert_not_called()
        self.assert_ordered_and_evaluated(period_records, ordered)

    def test_order_by_includes_id_tiebreaker_and_preserves_result_order(self):
        timestamp = datetime(2026, 11, 16, tzinfo=SEOUL)
        # The mock supplies the order: this verifies the ORM arguments and
        # serialization order, not the database's actual sorting behavior.
        ordered = self.ordered_result(self.records, [
            self.record(record_id=i, started_at=timestamp) for i in (3, 2, 1)
        ])
        response = self.client.get("/mission-sessions")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["id"] for r in response.json()["records"]], [3, 2, 1])
        self.manager.filter.assert_called_once_with(user=self.user)
        self.records.filter.assert_not_called()
        self.assert_ordered_and_evaluated(self.records, ordered)

    def test_delete_ignores_filters_and_preserves_other_users(self):
        other_records = MagicMock()
        self.manager.filter.side_effect = lambda *, user: (
            self.records if user is self.user else other_records
        )
        response = self.client.delete("/mission-sessions?status=INVALID&period=INVALID")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.manager.filter.assert_called_once_with(user=self.user)
        self.records.filter.assert_not_called()
        self.records.delete.assert_called_once_with()
        self.manager.delete.assert_not_called()
        other_records.delete.assert_not_called()

    def test_delete_empty_records(self):
        self.records.delete.return_value = (0, {})
        response = self.client.delete("/mission-sessions")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.manager.filter.assert_called_once_with(user=self.user)
        self.records.delete.assert_called_once_with()
