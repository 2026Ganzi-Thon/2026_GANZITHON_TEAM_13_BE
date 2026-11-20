from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.missions.models import Mission
from apps.sessions.models import MissionSession


SEOUL = ZoneInfo("Asia/Seoul")
WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
SUMMARY_URL = "/statistics/summary"


class SummaryRequestTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_invalid_period_returns_400_without_querying_the_database(self):
        self.client.force_authenticate(user=SimpleNamespace(pk=1, is_authenticated=True))
        for params in ({}, {"period": ""}, {"period": "week"}, {"period": "yearly"}):
            with self.subTest(params=params):
                response = self.client.get(SUMMARY_URL, params)
                self.assertEqual(response.status_code, 400)
                self.assertIn("period", response.json())

    def test_user_id_query_parameter_does_not_authenticate_the_request(self):
        response = self.client.get(SUMMARY_URL, {"period": "weekly", "user_id": 1})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Authentication required."})

    def test_anonymous_user_object_is_rejected(self):
        self.client.force_authenticate(user=AnonymousUser())
        response = self.client.get(SUMMARY_URL, {"period": "weekly"})
        self.assertEqual(response.status_code, 401)

    def test_unsupported_method_returns_405(self):
        self.assertEqual(reverse("statistics:summary"), SUMMARY_URL)
        response = self.client.post(SUMMARY_URL, {"period": "weekly"}, format="json")
        self.assertEqual(response.status_code, 405)
        self.assertIn("GET", response["Allow"].split(", "))


class SummaryAggregationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="summary-owner")
        cls.other_user = get_user_model().objects.create_user(username="other-owner")
        cls.mission = Mission.objects.create(
            title="Test mission",
            description="Test",
            category=Mission.Category.INDOOR,
            duration_seconds=60,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def session(
        self, completed_at, *, status=MissionSession.Status.COMPLETED, user=None,
        started_at=None,
    ):
        return MissionSession.objects.create(
            user=self.user if user is None else user,
            mission=self.mission,
            status=status,
            started_at=started_at or completed_at or timezone.now(),
            completed_at=completed_at,
        )

    def request_summary(self, period, now, **query_params):
        with patch("apps.statistics.services.timezone.now", return_value=now):
            response = self.client.get(SUMMARY_URL, {"period": period, **query_params})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def assert_summary(self, result, period, start, end, active_days, counts):
        self.assertEqual(result, {
            "period": period,
            "timeZone": "Asia/Seoul",
            "startDate": start,
            "endDate": end,
            "completedMissionCount": sum(counts),
            "activeDayCount": active_days,
            "weekdayCompletions": [
                {"weekday": weekday, "completedCount": count}
                for weekday, count in zip(WEEKDAYS, counts)
            ],
        })

    def test_weekly_counts_repeated_completions_and_uses_korean_dates(self):
        start = datetime(2026, 11, 16, tzinfo=SEOUL)
        end = start + timedelta(days=7)
        tick = timedelta(microseconds=1)
        self.session(start - tick)
        self.session(start.astimezone(UTC), started_at=start - timedelta(hours=1))
        self.session(start + timedelta(hours=12))
        self.session(end - tick)
        self.session(end, started_at=end - timedelta(hours=1))

        with timezone.override("UTC"), self.assertNumQueries(1):
            result = self.request_summary("weekly", (end - tick).astimezone(UTC))
        self.assert_summary(
            result, "weekly", "2026-11-16", "2026-11-22", 2, (2, 0, 0, 0, 0, 0, 1)
        )

    def test_repeated_period_is_rejected(self):
        for query in ("period=weekly&period=monthly", "period=invalid&period=weekly"):
            with self.subTest(query=query):
                response = self.client.get(f"{SUMMARY_URL}?{query}")
                self.assertEqual(response.status_code, 400)
                self.assertIn("period", response.json())

    def test_week_rolls_over_at_monday_midnight_in_seoul(self):
        monday = datetime(2026, 11, 15, 15, tzinfo=UTC)
        sunday = monday - timedelta(microseconds=1)
        self.session(sunday)
        self.session(monday)

        previous = self.request_summary("weekly", sunday)
        self.assert_summary(
            previous, "weekly", "2026-11-09", "2026-11-15", 1, (0, 0, 0, 0, 0, 0, 1)
        )
        current = self.request_summary("weekly", monday)
        self.assert_summary(
            current, "weekly", "2026-11-16", "2026-11-22", 1, (1, 0, 0, 0, 0, 0, 0)
        )

    def test_monthly_groups_matching_weekdays_and_includes_leap_day(self):
        start = datetime(2024, 2, 1, tzinfo=SEOUL)
        end = datetime(2024, 3, 1, tzinfo=SEOUL)
        tick = timedelta(microseconds=1)
        self.session(start - tick)
        self.session(start)
        self.session(datetime(2024, 2, 5, 10, tzinfo=SEOUL))
        self.session(datetime(2024, 2, 12, 10, tzinfo=SEOUL))
        self.session(end - tick)
        self.session(end)

        result = self.request_summary("monthly", end - tick)
        self.assert_summary(
            result, "monthly", "2024-02-01", "2024-02-29", 4, (2, 0, 0, 2, 0, 0, 0)
        )

    def test_records_are_scoped_to_authenticated_user_status_and_completion_time(self):
        now = datetime(2026, 11, 18, 12, tzinfo=SEOUL)
        self.session(now)
        self.session(now, user=self.other_user)
        self.session(now, status=MissionSession.Status.IN_PROGRESS)
        self.session(now, status=MissionSession.Status.CANCELLED)
        self.session(None, started_at=now)

        result = self.request_summary("weekly", now, user_id=self.other_user.pk)
        self.assert_summary(
            result, "weekly", "2026-11-16", "2026-11-22", 1, (0, 0, 1, 0, 0, 0, 0)
        )

    def test_korean_current_period_can_already_be_in_the_next_year(self):
        now = datetime(2025, 12, 31, 15, 30, tzinfo=UTC)
        self.session(now - timedelta(hours=1))
        self.session(now)

        december = self.request_summary("monthly", now - timedelta(hours=1))
        self.assert_summary(
            december, "monthly", "2025-12-01", "2025-12-31", 1, (0, 0, 1, 0, 0, 0, 0)
        )
        january = self.request_summary("monthly", now)
        self.assert_summary(
            january, "monthly", "2026-01-01", "2026-01-31", 1, (0, 0, 0, 1, 0, 0, 0)
        )

    def test_empty_period_returns_all_seven_weekdays_with_zero_counts(self):
        now = datetime(2026, 11, 18, tzinfo=SEOUL)
        result = self.request_summary("weekly", now)
        self.assert_summary(result, "weekly", "2026-11-16", "2026-11-22", 0, (0,) * 7)

    def test_deleted_records_are_no_longer_counted(self):
        now = datetime(2026, 11, 18, tzinfo=SEOUL)
        self.session(now)
        self.session(now, user=self.other_user)
        self.assertEqual(self.request_summary("monthly", now)["completedMissionCount"], 1)
        MissionSession.objects.filter(user=self.user).delete()

        result = self.request_summary("monthly", now)
        self.assert_summary(result, "monthly", "2026-11-01", "2026-11-30", 0, (0,) * 7)
