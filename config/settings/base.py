import os

from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 1️⃣ 먼저 공통 .env 로드 (ENV_MODE 읽기 위해)
base_env_path = BASE_DIR / "env" / ".env"
if base_env_path.exists():
    load_dotenv(base_env_path)

# 2️⃣ ENV_MODE 결정
ENV_MODE = os.getenv("ENV_MODE", "local").lower()

env_map = {
    "local": ".env.local",
    "develop": ".env.develop",
    "production": ".env.production",
}

env_file = env_map.get(ENV_MODE, ".env.local")
env_path = BASE_DIR / "env" / env_file

# 3️⃣ 환경별 env 로드
if env_path.exists():
    load_dotenv(env_path, override=True)

SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("DJANGO_SECRET_KEY", "change-me-in-production")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes") or os.getenv("DJANGO_DEBUG", "0") == "1"

_allowed = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]
if not _allowed and os.getenv("DJANGO_ALLOWED_HOSTS"):
    _allowed = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
ALLOWED_HOSTS = _allowed if _allowed else ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",  # CORS 헤더 지원
    "core",
    "api",  # 관리자 회원 모델 포함
    "sites.admin_api",
    "sites.admin_api.articles",  # 아티클 관리 앱
    "sites.admin_api.content_author",  # 콘텐츠 저자 관리 앱
    "sites.admin_api.homepage_doc",  # 홈페이지 정적 문서
    "sites.admin_api.curation",  # 특집(큐레이션) 콘텐츠
    "sites.admin_api.video",  # 비디오/세미나 (마이그레이션: video 테이블 스키마)
    "sites.admin_api.messages",  # 문자/카카오/이메일 발송 관리
    "sites.public_api",
    "apps.notice",
    "apps.faq",
    "apps.inquiry",
    "apps.content_question",
    "apps.content_comments",
    "apps.highlight",
    "apps.display_event",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS 미들웨어 (가장 위에 위치)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.CurrentSiteMiddleware",
    "config.middleware.SiteCorsMiddleware",  # site_meta['cors'] 기준 CORS (실서버 보장)
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "inde"),
        "USER": os.getenv("DB_USER", "inde"),
        "PASSWORD": os.getenv("DB_PASSWORD", "inde"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            # MySQL 1267(collation mix) 방지: 연결·리터럴·CAST 결과를 utf8mb4_unicode_ci로 통일
            "init_command": "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"

USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
# 1:1 문의 첨부 등 사용자 업로드 (nginx 등에서 /media/ 프록시 가능)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 커스텀 사용자 모델
AUTH_USER_MODEL = 'core.Account'

# REST Framework 설정
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'core.renderers.IndeJSONRenderer',
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': None,  # 페이지네이션은 각 뷰에서 직접 처리
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# CORS 설정 (env에 있으면 사용, 없으면 기본 목록). Django 4.0+ 요구: scheme 필수.
def _normalize_origin(o):
    o = (o or "").strip()
    if o and not o.startswith(("http://", "https://")):
        return "http://" + o
    return o


_cors_raw = [h.strip() for h in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if h.strip()]
_cors_origins = [_normalize_origin(o) for o in _cors_raw if _normalize_origin(o)]
CORS_ALLOWED_ORIGINS = _cors_origins if _cors_origins else [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "https://dev.inde.kr",
    "http://dev.inde.kr",
]
CORS_ALLOW_CREDENTIALS = True

# AWS S3 설정
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'ap-northeast-2')
AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN', '')  # CloudFront 도메인 등 (선택)

# 환경별 버킷 이름
# local/development: inde-develope
# production: inde-production
AWS_STORAGE_BUCKET_NAME_DEVELOPMENT = os.getenv('AWS_STORAGE_BUCKET_NAME_DEVELOPMENT', 'inde-develope')
AWS_STORAGE_BUCKET_NAME_PRODUCTION = os.getenv('AWS_STORAGE_BUCKET_NAME_PRODUCTION', 'inde-production')

# 명시적으로 버킷 이름을 지정할 경우 (환경별 자동 선택보다 우선)
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', '')
CORS_ALLOW_ALL_ORIGINS = False  # 프로덕션에서는 False로 설정

# CORS 허용 메서드
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

# CORS 허용 헤더
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    # TUS 프로토콜 헤더
    "upload-length",
    "upload-metadata",
    "upload-offset",
    "upload-defer-length",
    "upload-expires",
    "tus-resumable",
]

# CSRF 신뢰할 수 있는 Origin 설정 (env에서 읽거나 기본값). Django 4.0+ 요구: scheme 필수.
_csrf_raw = [h.strip() for h in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if h.strip()]
_csrf_origins = [_normalize_origin(o) for o in _csrf_raw if _normalize_origin(o)]
CSRF_TRUSTED_ORIGINS = _csrf_origins if _csrf_origins else [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# OAuth/인증 메일 등 프론트 리다이렉트 베이스 URL
PUBLIC_VERIFY_BASE_URL = (os.getenv("PUBLIC_VERIFY_BASE_URL") or "").strip().rstrip("/")

# SNS crawler OG HTML의 canonical/og:url 생성용 WWW origin.
# 예: https://inde.kr 또는 https://www.inde.kr
PUBLIC_WWW_ORIGIN = (
    os.getenv("PUBLIC_WWW_ORIGIN")
    or os.getenv("NEXT_PUBLIC_SITE_ORIGIN")
    or os.getenv("NEXT_PUBLIC_WWW_ORIGIN")
    or "https://inde.kr"
).strip().rstrip("/")

# 1:1 문의 답변 메일 내 열람 추적 픽셀 (public_api 절대 URL, 예: https://api.inde.kr)
INQUIRY_EMAIL_TRACK_BASE_URL = (os.getenv("INQUIRY_EMAIL_TRACK_BASE_URL") or "").strip().rstrip("/")

# JWT 설정
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_EXPIRATION_DELTA = 15 * 60  # 15분
JWT_REFRESH_EXPIRATION_DELTA = 7 * 24 * 60 * 60  # 7일

# public_api — refresh JWT HttpOnly 쿠키 (frontend_www / frontend_wwwRules.md §3)
# www 미들웨어가 refresh를 읽으려면 프로덕션에서 Domain을 공통 eTLD로 둠 (예: .inde.kr)
PUBLIC_JWT_REFRESH_COOKIE_NAME = os.getenv('PUBLIC_JWT_REFRESH_COOKIE_NAME', 'refreshToken')
_public_refresh_domain = os.getenv('PUBLIC_JWT_REFRESH_COOKIE_DOMAIN', '').strip()
PUBLIC_JWT_REFRESH_COOKIE_DOMAIN = _public_refresh_domain or None
PUBLIC_JWT_REFRESH_COOKIE_SAMESITE = os.getenv('PUBLIC_JWT_REFRESH_COOKIE_SAMESITE', 'Lax')
# True면 POST /auth/tokenrefresh 에서 수신한 refresh JWT 전체를 로그(운영 비권장). 미설정 시 DEBUG 와 동일.
_tvr = os.getenv('PUBLIC_JWT_TOKENREFRESH_VERBOSE_LOG', '').strip().lower()
if _tvr in ('1', 'true', 'yes'):
    PUBLIC_JWT_TOKENREFRESH_VERBOSE_LOG = True
elif _tvr in ('0', 'false', 'no'):
    PUBLIC_JWT_TOKENREFRESH_VERBOSE_LOG = False
else:
    PUBLIC_JWT_TOKENREFRESH_VERBOSE_LOG = DEBUG

# admin_api — 관리자 refresh JWT HttpOnly (frontend_adminRules.md, /adminMember/tokenrefresh)
ADMIN_JWT_REFRESH_COOKIE_NAME = os.getenv('ADMIN_JWT_REFRESH_COOKIE_NAME', 'adminRefreshToken')
_admin_refresh_domain = os.getenv('ADMIN_JWT_REFRESH_COOKIE_DOMAIN', '').strip()
ADMIN_JWT_REFRESH_COOKIE_DOMAIN = _admin_refresh_domain or None
ADMIN_JWT_REFRESH_COOKIE_SAMESITE = os.getenv('ADMIN_JWT_REFRESH_COOKIE_SAMESITE', 'Lax')

# Aligo SMS — 휴대폰 인증 (phoneVerificationAligo.md)
ALIGO_API_KEY = (os.getenv("ALIGO_API_KEY") or "").strip()
ALIGO_USER_ID = (os.getenv("ALIGO_USER_ID") or "").strip()
ALIGO_SENDER = (os.getenv("ALIGO_SENDER") or "").strip()
# 카카오 알림톡(알리고 akv10) — 발신프로필 키·테스트모드
ALIGO_KAKAO_SENDERKEY = (os.getenv("ALIGO_KAKAO_SENDERKEY") or "").strip()
ALIGO_KAKAO_TEST_MODE = os.getenv("ALIGO_KAKAO_TEST_MODE", "N").strip().upper() in ("Y", "1", "YES", "TRUE")
# True: 발송 직전 로그에 apikey·senderkey 등 비밀값까지 curl과 동일하게 기록(로그 유출 주의)
ALIGO_LOG_FULL_OUTBOUND = os.getenv("ALIGO_LOG_FULL_OUTBOUND", "").lower() in ("1", "true", "yes", "y")
SMS_SERVICE_NAME = (os.getenv("SMS_SERVICE_NAME") or "INDE").strip()
# DEBUG이고 SMS_SKIP_SEND=1 일 때만: SMS 미발송, 검증 로직은 동일(로그에 코드 출력)
SMS_SKIP_SEND = DEBUG and os.getenv("SMS_SKIP_SEND", "").lower() in ("1", "true", "yes")

# 파일 업로드 크기 제한 설정 (2GB)
# DATA_UPLOAD_MAX_MEMORY_SIZE: 메모리에 로드할 수 있는 최대 데이터 크기
# FILE_UPLOAD_MAX_MEMORY_SIZE: 메모리에 로드할 수 있는 최대 파일 크기
# 큰 파일은 임시 파일로 저장되므로 이 값보다 큰 파일도 업로드 가능
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

# 파일 업로드 디렉토리 설정
FILE_UPLOAD_TEMP_DIR = None  # 시스템 기본 임시 디렉토리 사용
FILE_UPLOAD_PERMISSIONS = 0o644  # 파일 권한
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755  # 디렉토리 권한

# 마이그레이션 보호장치
import sys
if os.getenv("DISALLOW_MIGRATE", "0") == "1" and "migrate" in sys.argv:
    raise SystemExit("Migrations are disabled in this environment.")

# runserver 요청 로그("GET /api/..." 한 줄씩, 로그 모듈명은 basehttp) — django.server INFO
# 기본은 WARNING으로 숨김. 다시 보려면 env에 DJANGO_RUNSERVER_ACCESS_LOG=1
_RUNSERVER_ACCESS_LEVEL = (
    "INFO"
    if os.getenv("DJANGO_RUNSERVER_ACCESS_LOG", "").lower() in ("1", "true", "yes")
    else "WARNING"
)

# 로그 디렉터리 (FileHandler / TimedRotatingFileHandler가 파일 생성 전에 필요)
(BASE_DIR / 'logs').mkdir(parents=True, exist_ok=True)

# 로깅 설정 — 파일은 자정마다 회전되어 `django.log.YYYY-MM-DD` 형태로 보관
_LOG_FILE_COMMON = {
    'formatter': 'verbose',
    'encoding': 'utf-8',
    'when': 'midnight',
    'interval': 1,
    'backupCount': 90,
    'utc': False,
}

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            **_LOG_FILE_COMMON,
        },
        'profile_update_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'profile_update.log'),
            **_LOG_FILE_COMMON,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console', 'file'],
            'level': _RUNSERVER_ACCESS_LEVEL,
            'propagate': False,
        },
        'sites.admin_api.articles': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'core.s3_storage': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'core': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'sites.public_api': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'sites.admin_api.messages': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'inde.profile_update': {
            'handlers': ['console', 'profile_update_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

