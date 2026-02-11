import os

from django.core.wsgi import get_wsgi_application

# 프로덕션 환경에서는 환경 변수로 설정 모듈을 지정
# 환경 변수가 없으면 기본값으로 local 사용 (개발 환경)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "config.settings.local"))

application = get_wsgi_application()

