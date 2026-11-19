from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.missions.models import Mission
from apps.sessions.models import MissionSession


SEOUL = ZoneInfo("Asia/Seoul")
GROWTH_URL = "/statistics/growth"


class GrowthRequestTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_period_must_be_one_supported_value(self):
        self.client.force_authenticate(user=SimpleNamespace(pk=1, is_authenticated=True))
        for query in ("", "?period=", "?period=week", "?period=weekly&period=monthly"):
            with self.subTest(query=query):
                response = self.client.get(GROWTH_URL + query)
                self.assertEqual(response.status_code, 400)
                self.assertIn("period", response.json())

    def test_unauthenticated_request_cannot_select_a_user(self):
        response = self.client.get(GROWTH_URL, {"period": "weekly", "user_id": 1})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Authentication required."})

    def test_unsupported_method_returns_405(self):
        self.assertEqual(reverse("statistics:growth"), GROWTH_URL)
        self.assertEqual(self.client.post(GROWTH_URL).status_code, 405)


class GrowthAggregationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="growth-owner")
        cls.other_user = get_user_model().objects.create_user(username="other-owner")
        cls.indoor = Mission.objects.create(
            title="Indoor", description="Test", category=Mission.Category.INDOOR,
            duration_seconds=60,
        )
        cls.outdoor = Mission.objects.create(
            title="Outdoor", description="Test", category=Mission.Category.OUTDOOR,
            duration_seconds=60,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def session(
        self, completed_at, *, mission=None, user=None, started_at=None,
        status=MissionSession.Status.COMPLETED,
    ):
        return MissionSession.objects.create(
            user=user or self.user,
            mission=mission or self.indoor,
            status=status,
            started_at=started_at or completed_at or timezone.now(),
            completed_at=completed_at,
        )

    def get_growth(self, period, as_of, **query):
        with patch("apps.statistics.services.timezone.now", return_value=as_of):
            response = self.client.get(GROWTH_URL, {"period": period, **query})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def assert_matches_summary(self, growth, as_of):
        with patch("apps.statistics.services.timezone.now", return_value=as_of):
            response = self.client.get("/statistics/summary", {"period": growth["period"]})
        self.assertEqual(response.status_code, 200)
        summary = response.json()
        self.assertEqual(
            growth["currentPeriod"],
            {key: summary[key] for key in ("startDate", "endDate", "completedMissionCount")},
        )

    def test_weekly_response_uses_korean_dates_and_excludes_ineligible_sessions(self):
        start = datetime(2026, 11, 15, 15, tzinfo=UTC)
        as_of = start + timedelta(days=2, hours=9)
        tick = timedelta(microseconds=1)
        self.session(start - timedelta(days=7) - tick)
        self.session(start - timedelta(days=7), mission=self.outdoor)
        self.session(start - tick, mission=self.outdoor)
        self.session(start, started_at=start - timedelta(hours=1))
        self.session(start + timedelta(hours=10))
        self.session(as_of, mission=self.outdoor)
        self.session(as_of + tick, mission=self.outdoor)
        self.session(start + timedelta(days=3))
        self.session(start + timedelta(days=7))
        self.session(start, user=self.other_user)
        self.session(start - tick, user=self.other_user)
        self.session(start, status=MissionSession.Status.IN_PROGRESS)
        self.session(start, status=MissionSession.Status.CANCELLED)
        self.session(None, started_at=start)

        with timezone.override("UTC"), self.assertNumQueries(1):
            result = self.get_growth("weekly", as_of, user_id=self.other_user.pk)
        self.assertEqual(result, {
            "period": "weekly",
            "timeZone": "Asia/Seoul",
            "currentPeriod": {
                "startDate": "2026-11-16", "endDate": "2026-11-22", "completedMissionCount": 3,
            },
            "previousPeriod": {
                "startDate": "2026-11-09", "endDate": "2026-11-15", "completedMissionCount": 2,
            },
            "growthRatePercent": 50.0,
            "categoryBreakdown": [
                {"category": "INDOOR", "completedMissionCount": 2, "percentage": 66.67},
                {"category": "OUTDOOR", "completedMissionCount": 1, "percentage": 33.33},
            ],
            "trend": [
                {"weekday": weekday, "date": f"2026-11-{day}", "completedMissionCount": count}
                for day, weekday, count in (
                    (16, "MON", 2), (17, "TUE", 0), (18, "WED", 1), (19, "THU", 0),
                    (20, "FRI", 0), (21, "SAT", 0), (22, "SUN", 0),
                )
            ],
        })
        self.assert_matches_summary(result, as_of)

    def test_monthly_trend_clips_both_ends_of_a_six_bucket_month(self):
        as_of = datetime(2026, 11, 19, tzinfo=SEOUL)
        for month, day in ((9, 30), (10, 1), (10, 31), (11, 1), (11, 2), (11, 8),
                           (11, 16), (11, 23), (11, 30), (12, 1)):
            self.session(datetime(2026, month, day, tzinfo=SEOUL))

        result = self.get_growth("monthly", as_of)
        self.assertEqual(result["currentPeriod"], {
            "startDate": "2026-11-01", "endDate": "2026-11-30", "completedMissionCount": 4,
        })
        self.assertEqual(result["previousPeriod"], {
            "startDate": "2026-10-01", "endDate": "2026-10-31", "completedMissionCount": 2,
        })
        self.assertEqual(result["trend"], [
            {
                "weekOfMonth": week, "startDate": f"2026-11-{start:02}",
                "endDate": f"2026-11-{end:02}", "completedMissionCount": count,
            }
            for week, start, end, count in (
                (1, 1, 1, 1), (2, 2, 8, 2), (3, 9, 15, 0),
                (4, 16, 22, 1), (5, 23, 29, 0), (6, 30, 30, 0),
            )
        ])
        self.assert_matches_summary(result, as_of)

    def test_january_uses_december_after_korean_new_year(self):
        january = datetime(2025, 12, 31, 15, tzinfo=UTC)
        december = january - timedelta(microseconds=1)
        self.session(december)
        self.session(january)

        result = self.get_growth("monthly", january)
        self.assertEqual(result["previousPeriod"], {
            "startDate": "2025-12-01", "endDate": "2025-12-31", "completedMissionCount": 1,
        })
        self.assertEqual(result["currentPeriod"], {
            "startDate": "2026-01-01", "endDate": "2026-01-31", "completedMissionCount": 1,
        })
        self.assertEqual(result["growthRatePercent"], 0)

    def test_leap_day_is_in_the_previous_month_at_march_midnight(self):
        march = datetime(2024, 3, 1, tzinfo=SEOUL)
        self.session(march - timedelta(microseconds=1))

        result = self.get_growth("monthly", march)
        self.assertEqual(result["previousPeriod"], {
            "startDate": "2024-02-01", "endDate": "2024-02-29", "completedMissionCount": 1,
        })
        self.assertEqual(result["growthRatePercent"], -100)

    def test_empty_four_week_month_returns_zero_counts_and_percentages(self):
        as_of = datetime(2021, 2, 1, tzinfo=SEOUL)
        result = self.get_growth("monthly", as_of)
        self.assertEqual(result["currentPeriod"]["endDate"], "2021-02-28")
        self.assertEqual(result["currentPeriod"]["completedMissionCount"], 0)
        self.assertEqual(result["previousPeriod"]["completedMissionCount"], 0)
        self.assertEqual(result["growthRatePercent"], 0)
        self.assertEqual(result["categoryBreakdown"], [
            {"category": "INDOOR", "completedMissionCount": 0, "percentage": 0},
            {"category": "OUTDOOR", "completedMissionCount": 0, "percentage": 0},
        ])
        self.assertEqual(len(result["trend"]), 4)
        self.assertTrue(all(bucket["completedMissionCount"] == 0 for bucket in result["trend"]))

    def test_current_completions_without_a_previous_baseline_have_null_growth(self):
        as_of = datetime(2026, 11, 18, tzinfo=SEOUL)
        self.session(as_of, mission=self.outdoor)

        result = self.get_growth("weekly", as_of)
        self.assertIsNone(result["growthRatePercent"])
        self.assertEqual(result["categoryBreakdown"][1]["percentage"], 100)

    def test_negative_growth_is_rounded_to_two_decimal_places(self):
        as_of = datetime(2026, 11, 18, tzinfo=SEOUL)
        for _ in range(3):
            self.session(as_of - timedelta(days=7))
        self.session(as_of)

        self.assertEqual(self.get_growth("weekly", as_of)["growthRatePercent"], -66.67)

    def test_category_breakdown_contains_only_the_models_declared_categories(self):
        as_of = datetime(2026, 11, 18, tzinfo=SEOUL)
        self.session(as_of)
        legacy_mission = Mission.objects.create(
            title="Legacy", description="Test", category="LEGACY", duration_seconds=60,
        )
        self.session(as_of, mission=legacy_mission)

        result = self.get_growth("weekly", as_of)
        self.assertEqual(result["currentPeriod"]["completedMissionCount"], 2)
        self.assertEqual(result["categoryBreakdown"], [
            {"category": "INDOOR", "completedMissionCount": 1, "percentage": 100},
            {"category": "OUTDOOR", "completedMissionCount": 0, "percentage": 0},
        ])
