from .base import *  # noqa: F403

DEBUG = True

# 개발 환경 설정
# 1. 먼저 env/.env를 로드하여 ENV_MODE 확인
# 2. ENV_MODE에 따라 env/.env.local 또는 env/.env.production 로드
from dotenv import load_dotenv
import os

# 메인 .env 파일 로드
main_env_path = os.path.join(BASE_DIR, 'env', '.env')
if os.path.exists(main_env_path):
    load_dotenv(main_env_path)

# ENV_MODE 확인하여 적절한 환경 변수 파일 로드
env_mode = os.getenv('ENV_MODE', 'local').lower()

if env_mode == 'production':
    env_path = os.path.join(BASE_DIR, 'env', '.env.production')
else:  # local 또는 기본값
    env_path = os.path.join(BASE_DIR, 'env', '.env.local')

if os.path.exists(env_path):
    load_dotenv(env_path, override=True)  # override=True로 메인 .env의 값을 덮어씀

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

