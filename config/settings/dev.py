from .base import *  # noqa: F403

DEBUG = True

# 개발 환경 설정
# .env 파일은 env/dev/.env 경로에서 로드
from dotenv import load_dotenv
import os

env_path = os.path.join(BASE_DIR, 'env', 'dev', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# 데이터베이스 설정 (개발)
DATABASES['default'].update({
    'NAME': os.getenv('DB_NAME', 'inde_dev'),
    'USER': os.getenv('DB_USER', 'inde'),
    'PASSWORD': os.getenv('DB_PASSWORD', 'inde'),
    'HOST': os.getenv('DB_HOST', '127.0.0.1'),
    'PORT': os.getenv('DB_PORT', '3306'),
})

# 개발 환경 도메인
ALLOWED_HOSTS = [
    'admin-api.inde.kr',
    'api.inde.kr',
    'localhost',
    '127.0.0.1',
]

# CORS 설정 (개발)
CORS_ALLOWED_ORIGINS = [
    "https://admin.inde.kr",
    "https://www.inde.kr",
]

