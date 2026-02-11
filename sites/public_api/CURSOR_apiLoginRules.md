웹페이지 로그인이기때문에 
public_api안에 구현
api.inde.kr도메인으로 호출됨


1-1. User 모델(커스텀 권장)
이메일을 아이디로 사용: USERNAME_FIELD = "email"
필수 필드(요구사항):
email (unique)
phone (unique 권장)
name
position (교회 직분)
birth_year, birth_month, birth_day
region_type (enum: DOMESTIC / FOREIGN)
region_domestic (도/광역시 값, DOMESTIC일 때 필수)
region_foreign (국가명/지역명, FOREIGN일 때 필수)
profile_completed (bool, default false)
joined_via (enum: LOCAL / KAKAO / NAVER / GOOGLE)
created_at, updated_at
비밀번호:로컬 가입은 password 필수
SNS 가입은 password nullable (또는 unusable password)

지역 입력 규칙(서버 검증 필수)
region_type == DOMESTIC 이면 region_domestic 필수, region_foreign는 null
region_type == FOREIGN 이면 region_foreign 필수, region_domestic는 null

1-2. SocialAccount 모델
user (FK)
provider (kakao/naver/google)
provider_user_id
email_from_provider (nullable)
connected_at, last_login_at
UNIQUE(provider, provider_user_id)
1-3. 인증 방식(권장)
백엔드에서 로그인 완료 시 JWT access/refresh를 HttpOnly 쿠키로 저장
access_token, refresh_token
HttpOnly; Secure; SameSite=None; Path=/
프론트는 API 호출 시 withCredentials / credentials: "include" 사용
/auth/refresh/ 엔드포인트로 access 재발급(쿠키 기반)
/auth/logout/ 는 쿠키 삭제
1-4. API 엔드포인트 설계 (필수 구현)
(A) 일반 회원가입/로그인
POST /auth/register/
입력: email, password, password2
동작: User 생성(기본정보 아직 없음) → profile_completed=false
응답: { ok:true }
POST /auth/login/
입력: email, password
동작: 인증 성공 시 쿠키 발급
응답: { ok:true, profile_completed: boolean }
GET /me/
인증 필요(쿠키)
응답: 유저 기본정보 + profile_completed
POST /auth/logout/
쿠키 삭제
(선택) POST /auth/password/reset/ 등은 추후
(B) 기본정보 입력(로컬 가입자 + SNS 가입자 공통)
PUT /profile/complete/
인증 필요(쿠키)
입력(필수):
email (읽기 전용 권장: 변경 불가 또는 별도 절차)
phone
name
position
birth_year, birth_month, birth_day
region_type (DOMESTIC/FOREIGN)
region_domestic or region_foreign (region_type에 따라)
서버에서 유효성 검사 후 저장
완료 시 profile_completed=true
응답: { ok:true, profile_completed:true }
(C) SNS OAuth (백엔드가 OAuth 처리)
GET /auth/{provider}/redirect/
provider: kakao|naver|google
state 생성/저장 후 공급자 authorize URL로 302 redirect
GET /auth/{provider}/callback/
code/state 수신, state 검증
토큰 교환 후 사용자 정보 조회
매칭 로직:
우선: SocialAccount(provider, provider_user_id) 있으면 해당 user 로그인
없으면 신규 user 생성(임시 상태):
email 제공되면 email 저장(단, 중복이면 보안정책 적용)
profile_completed=false
joined_via=provider
SocialAccount 생성
쿠키 발급 후 프론트로 302 redirect:
https://inde.kr/auth/callback
1-5. 이메일 중복 처리 정책(명확히 구현)
SNS에서 받은 email이 이미 로컬 계정으로 존재할 때:
정책 A(권장): “기존 계정으로 로그인 후 ‘SNS 연결’ 메뉴에서 연결” 유도
이 경우 callback에서 https://inde.kr/login?error=EMAIL_EXISTS로 redirect
자동 병합은 하지 않는다(보안/분쟁 위험)
1-6. Django 설정 (도메인 분리: inde.kr / api.inde.kr)
django-cors-headers:
CORS_ALLOWED_ORIGINS = ["https://inde.kr"]
CORS_ALLOW_CREDENTIALS = True
쿠키:
운영: Secure=True, SameSite=None
개발환경은 env로 분기
HTTPS 필수(secure cookie)