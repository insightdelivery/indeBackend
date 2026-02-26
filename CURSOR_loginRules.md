# 회원가입·로그인 규칙 (공개 API 백엔드)

## 1. 개요

- **사이트**: `sites/public_api` (PublicMemberShip 기반)
- **서버**: 포트 8001 (로컬), api.inde.kr (프로덕션)
- **인증**: JWT (access/refresh), Bearer 헤더 또는 쿠키 `accessToken`

---

## 2. 모델 (PublicMemberShip)

- **테이블**: `publicMemberShip`
- **일반 가입**: `joined_via='LOCAL'`, `password` 해시 저장, `email_verified=False` → 인증 메일 발송 후 링크 클릭 시 `True`
- **소셜 가입**: `joined_via='GOOGLE'`(또는 KAKAO/NAVER), `password=None`, `sns_provider_uid`=제공자 고유 ID, `email_verified=True`
- **구글 신규**: `profile_completed=False` → 프론트에서 부가정보 입력 후 `PUT /profile/complete/` 로 `True` 로 변경
- **필드**: member_sid(PK), email(unique), name, nickname, phone, position, birth_*, region_*, joined_via, sns_provider_uid, email_verified, profile_completed, is_active, last_login, created_at, updated_at

---

## 3. 엔드포인트

### 3.1 회원가입 (로컬)

- **POST** `/auth/register/` (또는 `/register/`, `/api/register/` 등)
- **동작**: PublicMemberShip 생성 (`email_verified=False`), 인증 메일 발송(코어 메일 라이브러리), **토큰 미반환**
- **응답**: `{ "success": true, "message": "...", "email": "...", "user": { id, email, name, nickname, phone, profile_completed } }`
- **메일**: `email_verification.create_verification_token(email)` → `get_verification_link(token)` → `send_verification_email(to_email, verify_url)`

### 3.2 로그인 (로컬)

- **POST** `/auth/login/`
- **동작**: email/password 검증, **`email_verified` 가 True 일 때만** 로그인 허용
- **미인증 시**: 403 `{ "error": "이메일 인증을 완료해 주세요. ..." }`
- **성공**: `{ "access_token", "refresh_token", "expires_in", "user" }`

### 3.3 이메일 인증

- **GET/POST** `/auth/verify-email/?token=...` 또는 body `{ "token": "..." }`
- **동작**: JWT 토큰 검증 → 해당 이메일 회원의 `email_verified=True` 저장
- **성공**: `{ "success": true, "message": "이메일 인증이 완료되었습니다. 로그인해 주세요." }`
- **실패**: 400 (토큰 없음/만료/불일치)

### 3.4 인증 메일 재발송

- **POST** `/auth/resend-verification-email/` body `{ "email": "..." }`
- **동작**: 해당 이메일·LOCAL·활성 회원 중 미인증이면 새 인증 메일 발송
- **응답**: 성공/이미 인증/계정 없음 모두 200 + 메시지 (보안상 동일 처리)

### 3.5 현재 사용자 (Me)

- **GET** `/me/`
  - **인증**: JWT 필수 (Bearer 또는 쿠키)
  - **응답**: `{ "id", "email", "name", "nickname", "phone", "profile_completed", "joined_via" }`
- **PATCH** `/me/`
  - **동작**: name, nickname, phone(필수), position, birth_*, region_*, newsletter_agree 수정 후 `profile_completed=True` 설정
  - **용도**: 구글 부가정보 완료 등

### 3.6 프로필 완료

- **PUT** `/profile/complete/`
  - **인증**: JWT 필수
  - **Body**: name, nickname, phone(필수), position, birth_year/month/day, region_type, region_domestic/region_foreign, newsletter_agree
  - **응답**: `{ "message": "프로필이 완료되었습니다.", "user": { ... } }`
  - **동작**: MeView.patch 와 동일하게 부가정보 저장 및 `profile_completed=True`

### 3.7 Google OAuth

- **GET** `/auth/google/redirect/?state=signup` (선택)
  - **동작**: Google 동의 화면 URL로 리다이렉트 (client_id, redirect_uri, scope=openid email profile)
  - **env**: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
- **GET** `/auth/google/callback/`
  - **동작**: code 교환 → Google userinfo → PublicMemberShip 조회/생성
    - 기존: `joined_via='GOOGLE'` & `sns_provider_uid` 일치 → 로그인
    - 동일 이메일 LOCAL 가입 존재 → 리다이렉트 `?error=EMAIL_ALREADY_REGISTERED`
    - 없으면 신규 생성: `email_verified=True`, `profile_completed=False`
  - **리다이렉트**: `{PUBLIC_VERIFY_BASE_URL}/auth/callback?access_token=...&refresh_token=...&expires_in=...&from=signup` (state=signup 일 때 from=signup)

---

## 4. 메일·인증 (별도 모듈)

- **메일 발송**: `core/mail.py` — `send_email(to_email, subject, body_html, body_text=None)`  
  - Gmail SMTP (smtp.gmail.com:587, TLS)  
  - **env**: `GMAIL_SENDER`, `GMAIL_APP_PASSWORD`(우선) 또는 `GOOGLE_API_KEY`(앱 비밀번호 16자, API 키 AIza 아님)
- **이메일 인증**: `sites/public_api/email_verification.py`
  - `create_verification_token(email)` — JWT, 24시간 유효, purpose `public_email_verify`
  - `verify_verification_token(token)` — 검증 후 email 반환
  - `get_verification_link(token)` — `{PUBLIC_VERIFY_BASE_URL}/auth/verify-email?token=...`
  - `send_verification_email(to_email, verify_url)` — core.mail 사용

---

## 5. 설정 (env)

| 변수 | 설명 |
|------|------|
| `JWT_SECRET_KEY` | JWT 서명 (기본 SECRET_KEY) |
| `PUBLIC_VERIFY_BASE_URL` | 인증 메일 링크의 프론트 베이스 (예: http://localhost:3001) |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth 클라이언트 ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth 클라이언트 시크릿 |
| `GMAIL_SENDER` | 인증 메일 발신 주소 |
| `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 (또는 GOOGLE_API_KEY에 앱 비밀번호) |

---

## 6. URL 목록 (public_api)

- `ping/`
- `auth/register/`, `auth/login/`
- `auth/verify-email/`, `auth/resend-verification-email/`
- `auth/google/redirect/`, `auth/google/callback/`
- `me/` (GET, PATCH)
- `profile/complete/` (PUT)
- `systemmanage/syscode/by_parent/`

---

## 7. 테스트 시나리오

- 로컬 가입 → 인증 메일 수신 → verify-email 호출 → 로그인 성공
- 로컬 로그인 시 email_verified=False → 403, resend-verification-email 후 인증
- 구글 가입 → callback → profile_completed=false → 프론트에서 complete-profile 제출 → profile_completed=true, 로그인 유지
- GET /me/ 는 JWT 필수, 없으면 401
