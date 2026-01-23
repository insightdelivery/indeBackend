from .base import *  # noqa: F403

DEBUG = False

# 프로덕션 환경 설정
# .env 파일은 env/.env.production 경로에서 로드
from dotenv import load_dotenv
import os

env_path = os.path.join(BASE_DIR, 'env', '.env.production')
if os.path.exists(env_path):
    load_dotenv(env_path)

# 데이터베이스 설정 (프로덕션)
DATABASES['default'].update({
    'NAME': os.getenv('DB_NAME', 'inde'),
    'USER': os.getenv('DB_USER', 'inde'),
    'PASSWORD': os.getenv('DB_PASSWORD', ''),
    'HOST': os.getenv('DB_HOST', '127.0.0.1'),
    'PORT': os.getenv('DB_PORT', '3306'),
})

# 프로덕션 환경 도메인
ALLOWED_HOSTS = [
    'api.inde.kr',
    'admin_api.inde.kr',  # 관리자 API 도메인
]

# CORS 설정 (프로덕션)
CORS_ALLOWED_ORIGINS = [
    "https://admin.inde.kr",
    "https://www.inde.kr",
]

# 보안 설정
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

