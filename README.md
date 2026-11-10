# 하루미션 백엔드

Django, Django REST Framework, MySQL, python-dotenv 기반 초기 프로젝트입니다.
Python 3.12 이상이 필요하며 로컬 검증 환경은 Python 3.13입니다.

## 로컬 실행 (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`의 `DJANGO_SECRET_KEY`를 임의의 긴 비밀값으로 변경하고 로컬 MySQL 접속 정보를 입력합니다.
비밀키는 다음 명령으로 생성할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

| 환경변수 | 용도 |
| --- | --- |
| DJANGO_SECRET_KEY | 필수 Django 비밀키 |
| DJANGO_DEBUG | 로컬 디버그 활성화 여부 (기본 False) |
| DJANGO_ALLOWED_HOSTS | 쉼표로 구분한 허용 호스트 |
| MYSQL_DATABASE | MySQL 데이터베이스명 |
| MYSQL_USER | MySQL 사용자 |
| MYSQL_PASSWORD | MySQL 비밀번호 |
| MYSQL_HOST | MySQL 호스트 |
| MYSQL_PORT | MySQL 포트 (기본 3306) |

`.env`는 Git에서 제외되며, 기존 시스템 환경변수가 `.env`보다 우선합니다.
MySQL 드라이버는 `mysqlclient`입니다. 호환 바이너리가 없는 환경에서 소스 빌드 시 MySQL 개발 라이브러리와 컴파일러가 필요할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

현재 단계는 모델 및 마이그레이션을 포함하지 않으며 `makemigrations`, `migrate`를 실행하지 않습니다.
개발 서버는 시작 시 마이그레이션 상태 확인을 위해 MySQL에 접속하므로,
`runserver`를 실행하려면 `.env`에 지정한 로컬 MySQL 데이터베이스와 계정이 준비되어 있어야 합니다.
위 기본 검사 및 테스트, 헬스 체크 뷰 자체는 MySQL 서버 없이 실행할 수 있습니다.
MySQL 접속 정보만 구성했으며 실제 DB 연결 검증이나 테이블 생성은 수행하지 않습니다.

## 헬스 체크

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health/
```

- 요청: `GET /api/health/`
- 응답: HTTP 200, `Content-Type: application/json`
- 본문: `{"status": "ok"}`
- 인증 및 DB 조회 없이 애플리케이션 응답 여부만 확인합니다.
- POST 등 지원하지 않는 메서드는 HTTP 405를 반환합니다.

## 구조

```text
config/          Django 설정, URL, ASGI/WSGI 진입점
health/          DRF 헬스 체크와 DB 미사용 테스트
manage.py        Django 관리 명령 진입점
requirements.txt 고정된 직접 의존성
.env.example     환경변수 예시 (실제 비밀값 제외)
```

인증, DB 모델 및 마이그레이션, 실제 기능 API, 배포 설정은 이번 단계의 범위에 포함하지 않습니다.

## 기능별 앱과 라우팅

```text
apps/
  missions/       미션 목록 및 추천
  sessions/       미션 수행 및 활동 기록
    views/
      actions.py  팀원 A: 시작, 완료, 취소
      history.py  팀원 B: 기록 조회, 전체 삭제
      endpoints.py  동일 경로의 HTTP 메서드 분기
  rest/           쉬기, 호흡, 건너뛰기 관련 기능
  places/         주변 장소 추천
  statistics/     통계 및 성장 기록
  notifications/  알림 설정
  tests.py        전체 기능 API 라우팅 검증
```

각 앱은 `apps.py`, `urls.py`와 뷰 모듈을 갖습니다.
`apps.statistics` 경로를 사용해 Python 표준 라이브러리 `statistics`와의 이름 충돌을 피합니다.
`apps.sessions`는 Django 내장 세션 앱과 별개의 기능 앱입니다. 내장 세션 앱은 등록하지 않았습니다.
`config/urls.py`에서 앱을 연결하고, 각 앱의 `urls.py` 한 곳에서 해당 앱의 경로를 관리합니다.

기능 API는 `/api` 접두사와 끝 슬래시를 사용하지 않습니다.
기존 `/api/health/`만 유지하며, 기능 API에 끝 슬래시를 붙이거나 `/api`를 추가하면 404입니다.
`APPEND_SLASH`의 기본 동작에 의존한 리다이렉트 없이 명세 경로로 요청해야 합니다.
지원하지 않는 기능 메서드는 405입니다. DRF의 자동 OPTIONS와 APIView의 HEAD 처리는 유지합니다.
모든 기능 API는 현재 HTTP 501과 `{"detail": "Not implemented yet"}`를 반환합니다.
모델, 인증, 실제 데이터 조회나 변경은 구현하지 않았습니다.
현재 라우터의 `<str:sessionId>`는 경로 값을 전달하기 위한 임시 설정이며,
API 계약의 식별자 자료형이나 허용 형식을 확정한 것이 아닙니다.

## 담당 API 및 엔드포인트

아래는 세션의 A/B 분리를 반영한 협업 분담안입니다. 나머지 배정은 팀 합의로 조정할 수 있습니다.

| 담당 | 메서드 | 경로 | 구현 위치 |
| --- | --- | --- | --- |
| A | GET | `/missions/random` | `apps/missions/views.py` |
| A | GET | `/missions` | `apps/missions/views.py` |
| A | POST | `/mission-sessions` | `apps/sessions/views/actions.py` |
| A | POST | `/mission-sessions/{sessionId}/complete` | `apps/sessions/views/actions.py` |
| A | POST | `/mission-sessions/{sessionId}/cancel` | `apps/sessions/views/actions.py` |
| B | GET | `/mission-sessions` | `apps/sessions/views/history.py` |
| B | DELETE | `/mission-sessions` | `apps/sessions/views/history.py` |
| B | GET | `/statistics/summary` | `apps/statistics/views.py` |
| B | GET | `/statistics/growth` | `apps/statistics/views.py` |
| B | GET | `/settings/notifications` | `apps/notifications/views.py` |
| B | PATCH | `/settings/notifications` | `apps/notifications/views.py` |
| C | GET | `/rest/guidance` | `apps/rest/views.py` |
| C | GET | `/rest/breathing` | `apps/rest/views.py` |
| C | POST | `/rest/records` | `apps/rest/views.py` |
| C | GET | `/rest/records/today` | `apps/rest/views.py` |
| C | GET | `/places/recommendations` | `apps/places/views.py` |

기존 `GET /api/health/`는 위 16개에 포함하지 않으며 HTTP 200을 유지합니다.

## 요청 파라미터와 미확정 사항

아래 표는 제공된 명세에서 확인된 파라미터 이름을 정리한 것입니다.
`sessionId`만 명시적으로 경로 변수이며, 나머지 파라미터가 query, JSON body,
form 등 어디에 위치하는지는 현재 제공된 정보만으로 확정하지 않습니다.
GET이나 POST라는 이유만으로 파라미터 위치를 결정하지 않습니다.

| 메서드 | 경로 | 파라미터 | 위치 | 필수 여부 | 자료형 | 기본값 |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/missions/random` | `category` | 미확정 | 미확정 | 미확정 | 미확정 |
| GET | `/missions` | `category` | 미확정 | 미확정 | 미확정 | 미확정 |
| POST | `/mission-sessions` | `missionId` | 미확정 | 미확정 | 미확정 | 미확정 |
| POST | `/mission-sessions/{sessionId}/complete` | `sessionId` | 경로 | 경로 매칭에 필요; 계약상 정의는 미확정 | 미확정 | 미확정 |
| POST | `/mission-sessions/{sessionId}/cancel` | `sessionId` | 경로 | 경로 매칭에 필요; 계약상 정의는 미확정 | 미확정 | 미확정 |
| GET | `/mission-sessions` | `status`, `period` | 각각 미확정 | 각각 미확정 | 각각 미확정 | 각각 미확정 |
| DELETE | `/mission-sessions` | 제공된 정보에 없음; 추가 유무 미확정 | 미확정 | 미확정 | 미확정 | 미확정 |
| GET | `/rest/guidance` | `type` | 미확정 | 미확정 | 미확정 | 미확정 |
| GET | `/rest/breathing` | 제공된 정보에 없음; 추가 유무 미확정 | 미확정 | 미확정 | 미확정 | 미확정 |
| POST | `/rest/records` | `type`, `breathingCompleted` | 각각 미확정 | 각각 미확정 | 각각 미확정 | 각각 미확정 |
| GET | `/rest/records/today` | 제공된 정보에 없음; 추가 유무 미확정 | 미확정 | 미확정 | 미확정 | 미확정 |
| GET | `/places/recommendations` | `missionId`, `latitude`, `longitude`, `radius` | 각각 미확정 | 각각 미확정 | 각각 미확정 | 각각 미확정 |
| GET | `/statistics/summary` | `period` | 미확정 | 미확정 | 미확정 | 미확정 |
| GET | `/statistics/growth` | `period` | 미확정 | 미확정 | 미확정 | 미확정 |
| GET | `/settings/notifications` | 제공된 정보에 없음; 추가 유무 미확정 | 미확정 | 미확정 | 미확정 | 미확정 |
| PATCH | `/settings/notifications` | `enabled`, `notificationTime` | 각각 미확정 | 각각 미확정 | 각각 미확정 | 각각 미확정 |

추가로 확정할 사항:

- 각 파라미터의 필수 여부, 자료형, 위치, 기본값 및 누락/null/빈 값 처리.
- 식별자 형식, category/status/period/type의 허용 값, 시간 형식과 시간대,
  좌표 및 radius의 단위와 범위. 이름만으로 숫자·불리언·시간 자료형을 가정하지 않습니다.
- 16개 기능 API 각각의 실제 성공 응답 상태·본문 구조와 오류 응답 구조.
  기존 501과 `{"detail": "Not implemented yet"}`는 임시 응답이며 최종 응답 명세가 아닙니다.

현재는 파라미터 파싱·검증·기본값 적용 및 비즈니스 로직을 구현하지 않습니다.
위 사항은 기존 명세나 팀 합의로 확정한 뒤 반영합니다.
기존 health의 HTTP 200 및 `{"status": "ok"}` 응답은 그대로 유지합니다.

## Git 브랜치 및 PR 협업 규칙

- 담당 기능별로 `feature/missions`, `feature/session-actions`, `feature/session-history`처럼 브랜치를 나눕니다.
- PR은 한 기능 단위로 나누고 변경 목적, 영향받는 API, 검사 및 테스트 결과를 기록합니다.
- 병합 전 다른 팀원에게 검토받고 기존 health와 전체 라우팅 테스트 통과를 확인합니다.
- 이번 로컬 작업에서는 commit, push, pull, fetch, 원격 브랜치 변경, PR 생성, 배포를 실행하지 않습니다. 향후 원격 작업은 사용자의 명시적 지시 범위에서만 수행합니다.
- `config/settings.py`, `config/urls.py`, 앱별 `urls.py`, `requirements.txt`, 공통 테스트는 공유 파일이므로 변경 전 담당자끼리 조율합니다.
- 세션의 A/B 담당자는 각자 `actions.py`, `history.py`에서 구현합니다. 공유 `endpoints.py`와 `urls.py` 변경은 함께 검토합니다.
- 공통 모델은 중복 작성하지 않습니다. 모델 소유 앱과 담당자를 먼저 합의하고 다른 앱에서는 해당 모델을 참조합니다.
- `Mission`, `MissionSession`, `rest_records`, `NotificationSetting` 모델을 이번 단계에서 생성하지 않습니다. 기존 DB 설계와 API 명세를 임의로 바꾸지 않습니다.
- User/AnonymousUser 모델이나 인증 방식은 별도 합의 전 결정하지 않습니다. 현재 공개 임시 응답 설정은 인증 설계의 확정을 의미하지 않습니다.
- DB 생성, `makemigrations`, `migrate`는 이번 작업 범위에서 실행하지 않습니다. `.env`와 실제 비밀값은 공유하거나 Git에 포함하지 않습니다.

## DB 없는 로컬 검증

위 로컬 설치 및 환경변수 설정 후 아래 명령을 실행합니다.

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --verbosity 2
git status --short
```

테스트는 `SimpleTestCase`를 사용해 DB 접근을 금지하고 테스트 DB 생성을 생략합니다.
16개 기능 API의 501 JSON, 경로 역참조, 미지원 메서드의 405,
끝 슬래시 및 `/api` 별칭의 404, 세션 담당 모듈 분기와 기존 health를 확인합니다.
