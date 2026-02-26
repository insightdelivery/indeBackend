# Inde Backend (Django REST Framework)

멀티사이트 아키텍처를 기반으로 한 Django REST Framework 프로젝트입니다.

## 아키텍처 개요

- **멀티사이트(Multi-Site) 아키텍처**: 도메인 기반 라우팅 구조
- **도메인별 독립 모듈**: 각 도메인은 독립된 URLConf, 인증 정책, CORS 설정을 가짐
- **사이트 모듈 분리**: `sites/` 디렉토리 하위에 사이트별 독립 모듈 구성

## 디렉토리 구조

```
backend/
├── config/              # 글로벌 설정 및 공용 미들웨어
│   ├── settings/        # 환경별 세팅 (base/local/dev/prod)
│   ├── site_router.py   # 도메인 ↔ URLConf 매핑
│   ├── middleware.py    # CurrentSiteMiddleware
│   └── urls.py          # 글로벌 URL (healthz 등 최소)
├── core/                # 공통 유틸리티, 서비스, 베이스 모델
│   ├── models.py        # Account, AuditLog 모델
│   ├── utils.py         # 공통 유틸리티 함수
│   └── renderers.py     # IndeJSONRenderer
├── sites/               # 사이트별 모듈
│   ├── admin_api/       # 관리자 API (admin_api.inde.kr)
│   └── public_api/      # 공개 API (api.inde.kr)
└── env/                 # 환경별 .env 파일
    ├── local/
    ├── dev/
    └── prod/
```

## 설치

### 1. 가상환경 생성 및 활성화

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

환경 변수 파일 구조:

```
env/
├── .env              # 메인 환경 변수 파일 (ENV_MODE 설정)
├── .env.local        # 로컬 환경 변수 파일
└── .env.production   # 프로덕션 환경 변수 파일
```

**env/.env** 파일 생성 (메인 환경 변수 파일):

```bash
# env/.env
# 환경 모드 설정 (local 또는 production)
ENV_MODE=local
```

**env/.env.local** 파일 생성 (로컬 환경):

```bash
# env/.env.local
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=1
DJANGO_SETTINGS_MODULE=config.settings.local

DB_NAME=inde
DB_USER=inde
DB_PASSWORD=inde
DB_HOST=127.0.0.1
DB_PORT=3306

JWT_SECRET_KEY=your-jwt-secret-key

# AWS S3 설정
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_S3_REGION_NAME=ap-northeast-2
AWS_STORAGE_BUCKET_NAME_DEVELOPMENT=inde-develope
AWS_STORAGE_BUCKET_NAME_PRODUCTION=inde-production
```

**env/.env.production** 파일 생성 (프로덕션 환경):

```bash
# env/.env.production
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=0
DJANGO_SETTINGS_MODULE=config.settings.prod

DB_NAME=inde
DB_USER=inde
DB_PASSWORD=your-production-password
DB_HOST=127.0.0.1
DB_PORT=3306

JWT_SECRET_KEY=your-jwt-secret-key

# AWS S3 설정
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_S3_REGION_NAME=ap-northeast-2
AWS_STORAGE_BUCKET_NAME_DEVELOPMENT=inde-develope
AWS_STORAGE_BUCKET_NAME_PRODUCTION=inde-production
```

**로드 순서:**
1. 먼저 `env/.env` 파일을 로드하여 `ENV_MODE` 값을 확인
2. `ENV_MODE=local`이면 `env/.env.local` 로드
3. `ENV_MODE=production`이면 `env/.env.production` 로드

## 실행

### 로컬 개발 환경

```bash
# 환경 변수 설정
export DJANGO_SETTINGS_MODULE=config.settings.local

# 서버 실행
python manage.py runserver 0.0.0.0:8000  # admin_api
# 또는
python manage.py runserver 0.0.0.0:8001  # public_api
```

### 로컬 테스트 URL

```bash
# Admin API (포트 8000)
curl http://localhost:8000/ping/
curl http://localhost:8000/healthz/

# Public API (포트 8001)
curl http://localhost:8001/ping/
curl http://localhost:8001/healthz/
```

## 사이트별 도메인 매핑

`config/site_router.py`에서 도메인과 사이트를 매핑합니다:

- `admin_api.inde.kr` / `localhost:8000` → `sites.admin_api`
- `api.inde.kr` / `localhost:8001` → `sites.public_api`

## 데이터베이스

- **데이터베이스**: MariaDB (MySQL)
- **마이그레이션**: 가이드라인에 따라 자동 마이그레이션은 금지됨
  - 마이그레이션 파일 생성: `python manage.py makemigrations` (허용)
  - 마이그레이션 적용: DBA 승인 후 수동으로 수행

### DB가 SQL 스크립트로만 생성된 경우 (테이블이 이미 있을 때)

테이블을 SQL로 먼저 만든 뒤 `migrate`를 돌리면 "Table already exists" 등으로 실패할 수 있습니다. 아래 순서로 맞춘 뒤 `migrate`를 사용하세요.

1. **이미 있는 테이블은 건너뛰고 적용**
   ```bash
   python manage.py migrate --fake-initial
   ```

2. **public_api 0002, 0003이 "already exists" / "Can't DROP INDEX" 로 실패하면** 해당 마이그레이션만 fake 처리
   ```bash
   python manage.py migrate public_api 0002_indeuser_socialaccount --fake
   python manage.py migrate public_api 0003_remove_socialaccount_socialaccou_user_id_idx_and_more --fake
   ```

3. **public_api 0004만 적용하고 싶을 때** (post_migrate 오류로 `migrate`가 실패하는 경우)
   ```bash
   DJANGO_SETTINGS_MODULE=config.settings.local python apply_public_api_0004_standalone.py
   ```
   이 스크립트는 `publicMemberShip`에 `sns_provider_uid` 추가·`member_sid` INT AUTO_INCREMENT 반영, 필요 시 `django_content_type.name` NULL 허용 처리, 그리고 `django_migrations`에 0004 기록까지 수행합니다.

4. **`migrate` 후 "Field 'name' doesn't have a default value" (django_content_type) 오류가 나면**
   ```sql
   ALTER TABLE django_content_type MODIFY COLUMN name VARCHAR(100) NULL DEFAULT NULL;
   ```
   실행 후 다시 `python manage.py migrate`를 실행합니다.

## 주요 기능

### 1. 공통 모델

- `core.Account`: 확장된 사용자 모델 (UUID, 전화번호, 생년월일 등)
- `core.AuditLog`: 사용자 활동 자동 로깅

### 2. API 응답 형식

모든 API 응답은 `IndeJSONRenderer`를 통해 자동으로 다음 형식으로 변환됩니다:

```json
{
  "IndeAPIResponse": {
    "ErrorCode": "00",
    "Message": "정상적으로 처리되었습니다.",
    "Result": { ... }
  }
}
```

### 3. 공통 유틸리티

`core/utils.py`에 다음 함수들이 제공됩니다:

- `create_success_response()`: 성공 응답 생성
- `create_error_response()`: 오류 응답 생성
- `create_custom_error_response()`: 커스텀 오류 응답 생성
- `generate_seq_code()`: 시퀀스 코드 생성
- `CommonUtils`: 공통 유틸리티 클래스

### 4. 페이지네이션

모든 리스트 조회 API는 페이지네이션을 지원합니다:

```python
# 파라미터
page = request.query_params.get('page', 1)
page_size = request.query_params.get('pageSize', 20)
```

## 개발 가이드

자세한 개발 가이드는 `.AI_GUIDELINES.md` 파일을 참조하세요.

## 주의사항

- **마이그레이션 자동 실행 금지**: `manage.py migrate`는 수동으로만 실행
- **모듈 Import 규칙**: 다른 프로젝트의 모듈을 직접 import하지 않음
- **API 응답 형식**: 뷰에서 `IndeAPIResponse` 래핑하지 않음 (렌더러가 자동 처리)
- **권한 체크**: 특별한 이야기가 없으면 무조건 권한 체크 필수
