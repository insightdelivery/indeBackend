from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "localhost:8000", "localhost:8001", "127.0.0.1:8000", "127.0.0.1:8001"]

# 로컬 개발 환경 설정
# .env 파일은 env/local/.env 경로에서 로드 (python-dotenv 사용)
from dotenv import load_dotenv
import os

env_path = os.path.join(BASE_DIR, 'env', 'local', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# 데이터베이스 설정 (로컬)
# SQLite 사용 (개발용 - MySQL/MariaDB가 없는 경우)
USE_SQLITE = os.getenv('USE_SQLITE', '0') == '1'

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # MySQL/MariaDB 사용
    DATABASES['default'].update({
        'NAME': os.getenv('DB_NAME', 'inde'),
        'USER': os.getenv('DB_USER', 'inde'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'inde'),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '3306'),
    })

# CORS 설정 (로컬 개발)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # 보안을 위해 False 유지

