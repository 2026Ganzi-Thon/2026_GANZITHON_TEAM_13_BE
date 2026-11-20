# 하루미션 백엔드

하루미션 백엔드는 **Django + Django REST Framework + MySQL** 기반 API 서버입니다. 회원가입·로그인 없이 브라우저 단위로 사용자를 구분할 수 있도록 **익명 사용자 생성 + JWT 인증**을 지원합니다.

- Python 3.12 이상 (로컬 검증: Python 3.13)
- Django 6.0.3 / Django REST Framework 3.17.1
- 데이터베이스: MySQL (`mysqlclient`)
- 인증: `djangorestframework-simplejwt` 5.5.1
- 개발용 FE 교차 출처 요청: `django-cors-headers` 4.9.0

> 구현 현황: 익명 사용자 발급·토큰 갱신, 미션 목록·추천, 미션 시작·완료·취소, 쉬기 안내·호흡법·기록 생성·오늘 기록 조회가 구현되어 있습니다. 일부 기록 조회·삭제, 통계, 알림, 장소 API는 아직 501 응답을 반환합니다. 아래 표를 참고하세요.

## 로컬 실행 (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`의 `DJANGO_SECRET_KEY`를 긴 임의의 비밀값으로 변경하고 로컬 MySQL 접속 정보를 입력합니다. 비밀키 생성 예시:

```powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

| 환경변수 | 용도 |
| --- | --- |
| `DJANGO_SECRET_KEY` | 필수 Django 비밀키·JWT 서명에 사용되는 기본 키 |
| `DJANGO_DEBUG` | 로컬 디버그 여부 (기본 `False`) |
| `DJANGO_ALLOWED_HOSTS` | 쉼표로 구분한 허용 호스트 |
| `MYSQL_DATABASE` | MySQL 데이터베이스명 |
| `MYSQL_USER` | MySQL 사용자 |
| `MYSQL_PASSWORD` | MySQL 비밀번호 |
| `MYSQL_HOST` | MySQL 호스트 |
| `MYSQL_PORT` | MySQL 포트 (기본 `3306`) |

`.env`는 Git에 올리지 않습니다. 실제 비밀키와 토큰도 저장소·이슈·채팅에 공개하지 마세요. 환경변수가 `.env` 값보다 우선합니다.

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py showmigrations
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

개발 서버는 MySQL 연결 및 적용된 마이그레이션 상태에 영향을 받습니다. 로컬 DB가 준비되어 있어야 하며, **마이그레이션은 각자의 로컬 DB에서 필요한 범위를 확인한 뒤 적용**합니다. 공유 DB에 대한 마이그레이션 실행은 담당자와 먼저 조율하세요.

```powershell
# 필요성이 확인된 로컬 DB에서만 실행
.\.venv\Scripts\python.exe manage.py migrate
```

Django 테스트 중 DB를 이용하는 테스트는 별도의 **테스트 DB를 생성·삭제**합니다. DB 생성 권한이 필요합니다. `apps.sessions`, `apps.rest`의 일부 기존 단위 테스트는 DB 접근 없이 실행됩니다.

### 개발용 CORS

현재 BE는 다음 FE 개발 서버 Origin을 허용합니다.

- `http://localhost:5173`
- `http://127.0.0.1:5173`

FE를 다른 포트나 도메인에서 실행한다면 `config/settings.py`의 `CORS_ALLOWED_ORIGINS`에 실제 Origin을 추가해야 합니다. 배포 시에는 운영 FE 주소만 허용하도록 조정합니다.

## 헬스 체크

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health/
```

- `GET /api/health/`: HTTP 200, `{"status": "ok"}`
- 인증·DB 조회 없이 서버 응답 여부 확인
- 이 경로는 예외적으로 `/api/` 접두사와 끝 슬래시를 사용합니다.

## 사용자 모델 및 데이터베이스 정책

- Django 기본 사용자 모델 `auth.User` 사용 (별도 커스텀 User 모델 없음)
- 사용자 데이터는 `auth_user` 테이블에서 관리
- 다른 모델에서는 `settings.AUTH_USER_MODEL` 참조
- `MissionSession.user_id`는 `auth_user.id`를 참조하는 외래 키
- `RestRecord`도 사용자 외래 키를 사용하며 사용자·날짜 기준으로 기록을 관리
- 익명 사용자는 랜덤한 `guest_...` 사용자명으로 생성하고 **사용할 수 없는 비밀번호**를 설정
- Django 기본 `auth.User.id`는 INT 계열이며, 미션 세션의 PK와 자료형이 다를 수 있습니다. 기존 DB 설계와의 일치 여부는 마이그레이션 변경 전에 확인해야 합니다.

**서비스 정책:** 별도의 회원가입·로그인 화면 없이 사용합니다. 동일 브라우저에서 저장된 인증 정보를 재사용하지만, 기기·브라우저 변경 또는 저장 정보 삭제 시 기존 사용자 복구는 보장하지 않습니다.

## 익명 사용자 인증 API

### 1. 익명 사용자 생성 — `POST /auth/guest`

인증 없이 호출합니다. 요청 Body는 필요하지 않습니다. **호출할 때마다 새로운** `auth.User`가 생성됩니다.

성공 응답: `201 Created`

```json
{
  "userId": 3,
  "accessToken": "<JWT_ACCESS_TOKEN>",
  "refreshToken": "<JWT_REFRESH_TOKEN>"
}
```

- `userId`: 서버가 생성한 사용자 PK (사용자 식별용 참고 정보, 인증 수단 아님)
- `accessToken`: 보호된 API 요청의 `Authorization` 헤더에 사용
- `refreshToken`: Access Token 재발급에 사용

FE는 **기존 인증 정보가 없거나 복구 불가능한 경우에만** 신규 사용자 발급을 요청해야 합니다. 단순 새로고침마다 호출하면 사용자가 계속 새로 생성됩니다.

### 2. Access Token 갱신 — `POST /auth/refresh`

요청 Body:

```json
{
  "refresh": "<JWT_REFRESH_TOKEN>"
}
```

성공 응답: `200 OK`

```json
{
  "access": "<NEW_ACCESS_TOKEN>"
}
```

현재 설정에서는 Refresh Token을 회전(재발급)하지 않습니다. 실패 시 토큰의 만료·손상 여부를 처리하고, 기존 사용자 복구가 불가능하면 새 익명 사용자를 발급해야 합니다.

### 3. 토큰 정책

| 토큰 | 유효 기간 | 용도 |
| --- | --- | --- |
| Access Token | 30분 | API 사용자 인증 |
| Refresh Token | 90일 | Access Token 갱신 |

실제 값은 `config/settings.py`의 `SIMPLE_JWT`를 기준으로 합니다. **토큰 갱신 성공이 Refresh Token 90일 만료 시점을 연장하는 것은 아닙니다.**

인증이 필요한 API에는 아래 헤더를 보냅니다.

```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
```

토큰이 없거나 유효하지 않으면 일반적으로 `401 Unauthorized`가 반환됩니다. 존재하지 않거나 다른 사용자에게 속한 미션 세션은 조회되지 않도록 처리합니다.

> **보안:** `userId`를 요청에 임의로 보내 인증을 대신하지 않습니다. 브라우저의 `localStorage`에 토큰을 저장하면 XSS에 의한 탈취 위험이 있으므로, 배포 전 토큰 보관 방식(예: HttpOnly·Secure 쿠키), HTTPS, 생성 요청 제한, 토큰 만료 및 에러 처리 정책을 점검해야 합니다. 현재 게스트 발급 API에는 기초적인 요청 제한이 적용되어 있습니다.

### 4. FE 연동 순서

1. 브라우저에서 저장된 토큰 확인
2. 저장된 인증 정보가 없으면 `POST /auth/guest` 호출 후 응답 저장
3. 보호된 API 호출 시 `Authorization: Bearer <accessToken>` 전송
4. Access Token 만료 시 `POST /auth/refresh`로 갱신한 `access` 저장 후 요청 재시도
5. Refresh Token까지 유효하지 않으면 기존 기록 복구를 보장하지 않고 새로운 익명 사용자 생성
6. 동시에 여러 API가 실행될 때 중복 게스트 생성·중복 토큰 갱신을 방지

FE는 미션 목록의 **BE가 반환한 `missionId`**를 사용하고, 미션 시작 응답의 `sessionId`를 완료·취소 호출에 사용해야 합니다.

## 기능별 앱과 라우팅

```text
apps/
  authentication/  익명 사용자 생성 및 JWT 갱신 URL·테스트
  missions/        미션 목록 및 무작위 추천
  sessions/        미션 시작·완료·취소, 활동 기록
    views/
      actions.py   시작·완료·취소
      history.py   기록 조회·전체 삭제 (현재 미구현)
      endpoints.py HTTP 메서드 분기 및 인증 권한
  rest/            쉬기 안내·호흡법·기록 생성·조회
  places/          주변 장소 추천 (현재 미구현)
  statistics/      통계·성장 기록 (현재 미구현)
  notifications/   알림 설정 (현재 미구현)
  tests.py         공통 API 라우팅 검증
config/            Django 설정, URL, ASGI/WSGI 진입점
health/            헬스 체크
manage.py          Django 관리 명령 진입점
requirements.txt   의존성 버전
.env.example       환경변수 예시
scripts/           미션 초기 데이터 SQL 등
```

`apps.sessions`는 Django 내장 세션 앱과 별개입니다. `apps.statistics`는 Python 표준 라이브러리 `statistics`와의 충돌을 피하기 위한 경로입니다.

**URL 규칙:** `GET /api/health/`만 예외이며, 나머지 기능·인증 API에는 `/api` 접두사나 끝 슬래시를 붙이지 않습니다. 인증이 필요한 엔드포인트에서는 미인증 요청이 메서드 검사 또는 미구현 응답보다 먼저 401로 처리될 수 있습니다.

## API 엔드포인트 및 구현 현황

아래는 기존 16개 기능 API와 새 인증 API 2개입니다. 상태는 이번 로컬 개발·테스트에서 확인된 구현을 기준으로 작성했습니다.

| 담당 | 메서드 | 경로 | 인증 | 구현 상태 |
| --- | --- | --- | --- | --- |
| 공통 | POST | `/auth/guest` | 불필요 | 구현·테스트 완료 |
| 공통 | POST | `/auth/refresh` | 불필요 | 구현·테스트 완료 |
| A | GET | `/missions/random` | 불필요 | 구현됨 |
| A | GET | `/missions` | 불필요 | 구현됨 |
| A | POST | `/mission-sessions` | 필요 | 구현됨 |
| A | POST | `/mission-sessions/{sessionId}/complete` | 필요 | 구현됨 |
| A | POST | `/mission-sessions/{sessionId}/cancel` | 필요 | 구현됨 |
| B | GET | `/mission-sessions` | 필요 | 501 (미구현) |
| B | DELETE | `/mission-sessions` | 필요 | 501 (미구현) |
| B | GET | `/statistics/summary` | 현행 기본 권한 AllowAny | 501 (미구현) |
| B | GET | `/statistics/growth` | 현행 기본 권한 AllowAny | 501 (미구현) |
| B | GET | `/settings/notifications` | 현행 기본 권한 AllowAny | 501 (미구현) |
| B | PATCH | `/settings/notifications` | 현행 기본 권한 AllowAny | 501 (미구현) |
| C | GET | `/rest/guidance` | 불필요 | 구현됨 |
| C | GET | `/rest/breathing` | 불필요 | 구현됨 |
| C | POST | `/rest/records` | 필요 | 구현됨 |
| C | GET | `/rest/records/today` | 필요 | 구현됨 |
| C | GET | `/places/recommendations` | 현행 기본 권한 AllowAny | 501 (미구현) |

`GET /api/health/`는 위 16개 기능 API에 포함되지 않습니다. `AllowAny`인 미구현 API의 인증 필요 여부는 담당자와 최종 정책을 확정해야 합니다.

### 현재 구현된 요청 형식 (주요 항목)

| 메서드·경로 | 요청 | 주요 응답 |
| --- | --- | --- |
| `GET /missions?category=INDOOR` | Query `category=INDOOR` 또는 `OUTDOOR` | `{"missions": [...]}` |
| `GET /missions/random?category=OUTDOOR` | Query `category=INDOOR` 또는 `OUTDOOR` | `missionId`, `title`, `description`, `category`, `durationSeconds`, `imageUrl` |
| `POST /mission-sessions` | JSON `{"missionId": 1}` + Bearer 토큰 | `201`, `sessionId`, `missionId`, `status`, `durationSeconds`, `startedAt` |
| `POST /mission-sessions/{sessionId}/complete` | Bearer 토큰 | `200`, `sessionId`, `missionId`, `status`, `completedAt`, `todayCompletedCount` |
| `POST /mission-sessions/{sessionId}/cancel` | Bearer 토큰 | `200`, `sessionId`, `missionId`, `status`, `cancelledAt` |
| `GET /rest/guidance?type=REST` | Query `type=REST` 또는 `SKIP` | `type`, `message` |
| `GET /rest/breathing` | 별도 파라미터 없음 | `inhaleSeconds`, `exhaleSeconds`, `repeatCount` |
| `POST /rest/records` | JSON `{"type":"REST"}` 또는 `SKIP`, 선택적 Boolean `breathingCompleted` + Bearer 토큰 | `201` 생성 또는 `200` 갱신, 기록 데이터 |
| `GET /rest/records/today` | Bearer 토큰 | `{"record": null}` 또는 기록 데이터 |

다음 항목은 구현 또는 팀 합의에 따라 조정해야 합니다: 미구현 API의 요청·응답 계약, 기간·상태 필터, 위치 파라미터 및 단위, 알림 설정 형식, 통계 API의 인증 필요 여부. 현재 501인 API를 기능이 완료된 것으로 간주하지 마세요.

## 로컬 검증 결과 및 추가 확인

이번 로컬 작업에서 확인한 사항:

- `python manage.py check` 통과
- `python manage.py test apps.sessions`: **12개 통과**
- `python manage.py test apps.rest`: **4개 통과**
- `python manage.py test apps.authentication`: **4개 통과**
- `python manage.py test`: **전체 32개 통과**
- 실제 로컬 API 호출에서 `POST /auth/guest` → JWT 발급, `POST /auth/refresh` → 갱신 확인
- JWT를 보낸 `POST /mission-sessions` → `201`, 완료 API → 정상 응답 확인
- 다른 익명 사용자가 기존 사용자 세션 완료를 요청할 경우 `404` 확인

이 결과는 **BE 로컬 검증**이며, 실제 FE 브라우저에서의 토큰 저장·자동 갱신·API 연동은 아직 별도 검증이 필요합니다. 또한 미션 취소와 인증 실패 세부 상황, 토큰 만료 경계 조건 등에 대한 추가 통합 테스트를 권장합니다.

이번 로컬 서버 실행 시 `rest` 앱에 **미적용 마이그레이션 1개** 경고가 있었습니다. 쉬기 기록 API를 로컬 DB에서 실제 사용하려면 해당 DB의 마이그레이션 상태를 확인하고 적용해야 합니다. 팀원별 독립적인 로컬 DB의 마이그레이션 적용 여부는 서로 다를 수 있습니다.

## Git 브랜치 및 협업 규칙

- 기능별 브랜치를 유지하고, 공통 설정(`config/settings.py`, `config/urls.py`, `requirements.txt`, 공통 테스트) 변경 시 담당자와 조율합니다.
- PR에는 변경 목적·영향 API·테스트 결과를 적고, 병합 전에 리뷰합니다.
- `mission` 등 기능 브랜치에 `main` 변경을 반영할 때는 로컬 미커밋 변경사항을 보존한 후 병합합니다.
- `.env`, 실제 JWT, 비밀키, 로컬 DB 덤프 등 민감 정보를 커밋하지 않습니다.
- DB 스키마·기존 API 명세를 임의로 바꾸지 않고 담당자와 논의합니다.

## FE 연동 가이드

FE에서 익명 사용자 JWT 인증 및 미션 API를 연동하는 방법은
[FE 연동 가이드](docs/FE_INTEGRATION_GUIDE.md)를 참고하세요.