from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIClient


class RestApiTests(SimpleTestCase):
    # DB 접근 없이 API 검증과 기록 처리 분기를 확인합니다.
    def setUp(self):
        self.client = APIClient()
        self.user = SimpleNamespace(id=1, is_authenticated=True)

    def test_guidance_and_breathing(self):
        self.assertEqual(self.client.get('/rest/guidance', {'type': 'REST'}).status_code, 200)
        self.assertEqual(self.client.get('/rest/guidance', {'type': 'other'}).status_code, 400)
        self.assertEqual(self.client.get('/rest/breathing').json(), {'inhaleSeconds': 4, 'exhaleSeconds': 6, 'repeatCount': 3})

    def test_records_require_authentication(self):
        self.assertEqual(self.client.post('/rest/records', {}, format='json').status_code, 401)
        self.assertEqual(self.client.get('/rest/records/today').status_code, 401)

    @patch('apps.rest.views.RestRecord.objects.update_or_create')
    def test_record_validation_and_update(self, update):
        # 완료 여부를 생략한 갱신이 기존 값을 덮어쓰지 않는지 확인합니다.
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.post('/rest/records', {'type': 'SKIP', 'breathingCompleted': 'false'}, format='json').status_code, 400)
        record = SimpleNamespace(id=1, type='SKIP', breathing_completed=True, record_date=date(2026, 1, 1), created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        update.return_value = (record, False)
        response = self.client.post('/rest/records', {'type': 'SKIP'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['breathingCompleted'])
        self.assertEqual(update.call_args.kwargs['defaults'], {'type': 'SKIP'})

    @patch('apps.rest.views.RestRecord.objects.filter')
    def test_no_record_today(self, query):
        self.client.force_authenticate(user=self.user)
        query.return_value.first.return_value = None
        self.assertEqual(self.client.get('/rest/records/today').json(), {'record': None})
