# config/settings/production.py
from .local import *  # local 설정을 기반으로 시작 (원하면 base.py로 분리해도 됨)

import os
from pathlib import Path

# 프로젝트 루트 (manage.py가 있는 폴더 기준으로 맞추기)
BASE_DIR = Path(__file__).resolve().parents[2]  # ~/inde_api

# ---- 1) env/.env.production 로드 (python-dotenv 사용) ----
# 프로젝트에 python-dotenv가 없으면 설치: pip install python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / "env" / ".env.production")
except Exception:
    # systemd EnvironmentFile / shell source 방식으로 넣을 수도 있으니 조용히 패스
    pass

# ---- 2) 운영 기본값 ----
DEBUG = os.getenv("DEBUG", "False").lower() in ("1", "true", "yes")

SECRET_KEY = os.getenv("SECRET_KEY", SECRET_KEY)  # local에 값이 있더라도 운영값 우선

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]
if not ALLOWED_HOSTS:
    # 최소 안전장치 (도메인 넣는 걸 추천)
    ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# ---- 3) DB (MySQL/RDS) ----
# local.py에서 이미 DATABASES가 있더라도 운영에서 덮어쓰기
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")

if DB_NAME and DB_USER and DB_PASSWORD and DB_HOST:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }

# ---- 4) Static/Media (원하는 경로로) ----
STATIC_ROOT = os.getenv("STATIC_ROOT", str(BASE_DIR / "staticfiles"))
MEDIA_ROOT = os.getenv("MEDIA_ROOT", str(BASE_DIR / "media"))

# ---- 5) 보안/프록시(nginx 뒤에 둘 때) ----
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() in ("1", "true", "yes")
