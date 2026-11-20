# 하루미션 FE–BE 연동 가이드 — 익명 사용자 인증

> FE 팀 전달용 · 기준: 2026-11-20 로컬 BE 구현 및 테스트 결과  
> BE 저장소: https://github.com/2026Ganzi-Thon/2026_GANZITHON_TEAM_13_BE  
> FE 저장소: https://github.com/2026Ganzi-Thon/2026_GANZITHON_TEAM_13_FE

## 1. 연동 핵심 요약

하루미션은 **회원가입·로그인 없이 이용**합니다. 사용자 구분은 브라우저 단위입니다. 브라우저에서 처음 접속하면 BE에 익명 사용자 생성을 요청하고, 반환된 JWT를 저장한 뒤 사용자별 기록 API 요청에 전달합니다. **다른 브라우저·기기에서 기록이 이어지지 않아도 되는 정책**입니다.

- 최초 접속: `POST /auth/guest` → `userId`, `accessToken`, `refreshToken` 발급
- 이후 요청: `Authorization: Bearer <accessToken>` 헤더 전송
- Access Token 만료: `POST /auth/refresh`로 재발급 → 저장된 토큰 갱신
- Refresh Token도 만료·무효: 새 익명 사용자 생성 (이전 기록 복구되지 않음)
- **`userId`를 미션 API 본문에 보내 사용자를 지정하지 않습니다.** BE가 JWT에서 사용자 정보를 판별합니다.

BE의 로컬 수동 테스트에서 익명 사용자 생성·토큰 갱신·미션 시작·완료·타 사용자 세션 차단이 확인되었고, 전체 자동 테스트 **32개 통과**했습니다. 이것이 FE 실제 브라우저 연동까지 검증했다는 뜻은 아닙니다.

## 2. 개발 환경 및 주소

BE 개발 서버 예시: `http://127.0.0.1:8000`  
FE Vite 개발 서버 예시: `http://localhost:5173`

FE 프로젝트 루트 `.env.local`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

**주의:** 기능 API는 `/api` 접두사나 끝 슬래시(`/`)를 붙이지 않습니다. 예: `/mission-sessions` (O), `/api/mission-sessions/` (X). 예외적으로 헬스 체크만 `/api/health/`입니다.

현재 BE CORS 허용 Origin은 `http://localhost:5173`, `http://127.0.0.1:5173`입니다. 다른 주소·포트에서 FE를 실행할 경우 BE CORS 설정 조정이 필요합니다. 각 개발자의 `localhost`는 각자 기기를 의미하므로 서로 다른 기기에서 접속할 때 BE 호스트 주소도 바꿔야 합니다.

## 3. 신규 인증 API 명세

### 3-1. 익명 사용자 생성

| 항목 | 값 |
| --- | --- |
| Method | `POST` |
| Path | `/auth/guest` |
| 인증 | 불필요 |
| 요청 Body | 없음 |
| 성공 | `201 Created` |

응답 예시(토큰 값은 예시 표기):

```json
{
  "userId": 3,
  "accessToken": "<JWT_ACCESS_TOKEN>",
  "refreshToken": "<JWT_REFRESH_TOKEN>"
}
```

**호출할 때마다 새 사용자 계정이 생성됩니다.** 첫 접속이나 기존 인증 정보를 복구할 수 없는 경우에만 호출해야 합니다. 토큰 발급 요청이 동시에 중복 실행되지 않도록 하나의 초기화 Promise를 공유하세요.

### 3-2. Access Token 갱신

| 항목 | 값 |
| --- | --- |
| Method | `POST` |
| Path | `/auth/refresh` |
| 인증 | 별도 Access Token 불필요 |
| 요청 헤더 | `Content-Type: application/json` |
| 성공 | `200 OK` |

요청:

```json
{
  "refresh": "<JWT_REFRESH_TOKEN>"
}
```

응답:

```json
{
  "access": "<NEW_ACCESS_TOKEN>"
}
```

**필드명 주의:** 최초 발급 응답은 `accessToken` / `refreshToken`, 갱신 응답은 `access`입니다. 현재 BE의 설정에서는 갱신 API가 새 Refresh Token을 반환하지 않습니다.

토큰 설정: Access Token **30분**, Refresh Token **90일**. 단, 브라우저에 저장한다고 90일 이상 동일 사용자가 무조건 유지되는 것은 아닙니다. Refresh Token 만료·삭제 시 기존 기록 복구를 보장하지 않습니다.

### 3-3. 보호 API 공통 헤더

```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
Content-Type: application/json
```

`Content-Type`은 JSON 요청 Body가 있을 때 사용합니다. `Bearer` 뒤에는 **Access Token**을 넣습니다(Refresh Token 아님).

## 4. 기존 API: 무엇을 언제 호출하나요?

| FE 동작 | Method | Path | JWT | BE 현황 |
| --- | --- | --- | --- | --- |
| 집 안/밖 미션 목록 조회 | GET | `/missions?category=INDOOR` 또는 `OUTDOOR` | 불필요 | 구현됨 |
| 랜덤 미션 추천 | GET | `/missions/random?category=INDOOR` 또는 `OUTDOOR` | 불필요 | 구현됨 |
| 미션 시작 | POST | `/mission-sessions` | 필수 | 구현됨 |
| 미션 완료 | POST | `/mission-sessions/{sessionId}/complete` | 필수 | 구현됨 |
| 미션 취소 | POST | `/mission-sessions/{sessionId}/cancel` | 필수 | 구현됨 |
| 쉬기/건너뛰기 안내 | GET | `/rest/guidance?type=REST` 또는 `SKIP` | 불필요 | 구현됨 |
| 호흡법 안내 | GET | `/rest/breathing` | 불필요 | 구현됨 |
| 쉬기/건너뛰기 기록 저장 | POST | `/rest/records` | 필수 | 구현됨 |
| 오늘의 쉬기 기록 조회 | GET | `/rest/records/today` | 필수 | 구현됨 |
| 미션 기록 전체 조회 | GET | `/mission-sessions` | 필수 | **아직 501** |
| 미션 기록 전체 삭제 | DELETE | `/mission-sessions` | 필수 | **아직 501** |
| 통계/성장/알림/장소 | 해당 경로 | 기존 BE README 참조 | 추후 확인 | **아직 501** |

### 4-1. 미션 시작

```http
POST /mission-sessions
Authorization: Bearer <accessToken>
Content-Type: application/json
```

```json
{"missionId": 1}
```

성공: `201 Created`

```json
{
  "sessionId": 4,
  "missionId": 1,
  "status": "IN_PROGRESS",
  "durationSeconds": 60,
  "startedAt": "2026-11-20T04:23:38.309023+00:00"
}
```

여기서 받은 **`sessionId`**를 미션 실행 화면의 상태에 보관해야 합니다. URL의 `missionId`와 `sessionId`는 서로 다른 값입니다. FE에서 하드코딩해 둔 미션 ID 대신 BE에서 조회한 실제 `missionId`를 사용하세요.

### 4-2. 미션 완료 및 취소

```http
POST /mission-sessions/4/complete
Authorization: Bearer <accessToken>
```

성공: `200 OK`, `status: "COMPLETED"`, `completedAt`, `todayCompletedCount` 등 반환.

```http
POST /mission-sessions/4/cancel
Authorization: Bearer <accessToken>
```

성공: `200 OK`, `status: "CANCELLED"`, `cancelledAt` 등 반환.

완료·취소 요청에는 **미션 시작 응답의 `sessionId`**가 필요합니다. 버튼을 누르자마자 로컬 기록만 저장하지 말고 서버 응답 성공을 확인한 뒤 완료 화면으로 이동하세요. 이미 완료되거나 취소된 세션에 재요청하면 `409`가 반환될 수 있습니다.

### 4-3. 쉬기/건너뛰기 저장

```http
POST /rest/records
Authorization: Bearer <accessToken>
Content-Type: application/json
```

```json
{"type":"SKIP","breathingCompleted":false}
```

`type`은 `REST` 또는 `SKIP`입니다. `breathingCompleted`는 선택적인 boolean입니다. 오늘 사용자 기록이 없으면 `201`, 기존 기록 갱신이면 `200`입니다. 오늘 기록 조회는 `GET /rest/records/today`입니다.

**BE 로컬 DB 주의:** 팀원별로 DB를 별도 운용 중입니다. 쉬기 기록 API의 실제 DB 저장 테스트에는 해당 환경에서 `rest` 마이그레이션이 적용되어 있어야 합니다. 현재 인증 담당 로컬에서는 미적용 경고가 확인되었으나, 담당 팀원 DB 상태와는 무관합니다.

## 5. FE 구현 순서

1. 페이지 진입 시 브라우저에 저장된 인증 정보를 확인합니다.
2. Access Token이 유효하면 재사용합니다. 만료되었으면 Refresh Token으로 갱신을 시도합니다.
3. 저장된 인증 정보가 없거나 Refresh Token까지 만료·무효한 경우에만 `/auth/guest`를 호출합니다.
4. 인증이 필요한 모든 API 요청에 `Authorization: Bearer ...`를 추가합니다.
5. 보호 API에서 401이 오면 갱신을 **한 번만** 시도하고 원래 요청을 **한 번만** 재시도합니다. 계속 실패하면 무한 반복하지 않습니다.
6. 미션 조회(`missions.ts`)의 하드코딩 목록을 BE 조회 결과로 교체합니다.
7. `Run.tsx`에서 미션 시작 시 `POST /mission-sessions`를 호출하고, 완료·취소에 `sessionId`를 사용합니다.
8. `records.ts`의 로컬 기록과 서버 기록의 역할을 정리합니다. 현재 BE의 전체 미션 기록 조회는 501이므로 기록 화면을 완전 연동하기 전에는 별도 대응이 필요합니다.
9. 홈/미션 화면의 쉬기·건너뛰기 동작을 `/rest/records`에 연결합니다.

### 참고 TypeScript 요청 예제 (기본 흐름)

```ts
const API_URL = import.meta.env.VITE_API_URL

async function createGuest() {
  const response = await fetch(`${API_URL}/auth/guest`, { method: 'POST' })
  if (!response.ok) throw new Error(`Guest creation failed: ${response.status}`)
  return response.json() as Promise<{
    userId: number
    accessToken: string
    refreshToken: string
  }>
}

async function refreshAccessToken(refreshToken: string) {
  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: refreshToken }),
  })
  if (!response.ok) throw new Error(`Token refresh failed: ${response.status}`)
  const data = (await response.json()) as { access: string }
  return data.access
}

async function startMission(missionId: number, accessToken: string) {
  const response = await fetch(`${API_URL}/mission-sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ missionId }),
  })
  if (!response.ok) throw new Error(`Mission start failed: ${response.status}`)
  return response.json() as Promise<{ sessionId: number; missionId: number; status: string }>
}
```

위 코드는 **API 형식을 보여주는 최소 예제**이며 저장소 관리, 만료 판단, 자동 갱신, 중복 요청 방지까지 구현한 완성형 인증 클라이언트는 아닙니다.

## 6. 상태 코드 및 FE 예외 처리

| 상태 코드 | 의미 / 권장 처리 |
| --- | --- |
| `200` | 조회·완료·취소·토큰 갱신 등 성공 |
| `201` | 익명 사용자 생성, 미션 시작, 신규 쉬기 기록 생성 성공 |
| `400` | 잘못된 입력/미션 ID/카테고리 등 → 요청값 확인 |
| `401` | 인증 누락·만료·유효하지 않은 토큰 → 갱신 후 제한된 재시도 |
| `404` | 미션이나 해당 사용자의 세션 없음 → ID 또는 접근 대상 확인 |
| `409` | 이미 완료/취소한 세션을 다시 처리하려는 상태 충돌 |
| `429` | 익명 사용자 생성 요청 제한 등 → 무한 재시도 금지 |
| `501` | 아직 구현되지 않은 API → FE에서 미구현 상태 처리 |

유효하지 않은 토큰을 보내는 것과 인증 없이 보내는 것은 모두 401일 수 있습니다. 보호 API 요청에서는 사용자 ID를 임의로 변경하는 방식으로 오류를 해결하지 않습니다.

## 7. 보안 및 배포 유의사항

- 사용자별 기록을 구분하는 것은 `userId` 본문 값이 아니라 **BE가 검증한 JWT**입니다.
- 로컬 저장소(localStorage)에 토큰을 두면 XSS 탈취 위험이 있습니다. 실제 배포 전 보관 방식(예: HttpOnly·Secure 쿠키)과 XSS 방어를 검토하세요.
- 브라우저 저장 정보가 사라지면 해당 익명 사용자로의 접근 복구가 불가능할 수 있습니다.
- 인증 토큰·`.env`·비밀키를 GitHub나 채팅에 올리지 마세요.
- 배포 환경은 HTTPS를 사용하고 CORS 허용 Origin을 실제 FE 주소로 제한하세요.
- 게스트 생성 API는 새 계정을 생성하므로 초기화/새로고침 때마다 반복 호출하지 마세요.

## 8. FE 담당자 검증 체크리스트

- [ ] 첫 접속에서 `/auth/guest` 호출이 한 번만 일어나고 토큰이 저장됨
- [ ] 새로고침/재접속에서 같은 인증 정보로 기존 사용자 유지
- [ ] 미션 목록에 BE `missionId` 사용
- [ ] 미션 시작 201 → `sessionId` 수신
- [ ] 완료 200 또는 취소 200 정상 처리
- [ ] Access Token 갱신 후 동일 사용자로 요청 계속 가능
- [ ] 브라우저 A/B에서 서로 다른 기록으로 분리
- [ ] 토큰 없는 보호 API는 401, 공개 API는 정상 조회
- [ ] 미구현 501 API를 화면에서 구분 처리

---