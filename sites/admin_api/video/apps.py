"""
비디오 앱 설정
"""
from django.apps import AppConfig


class VideoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sites.admin_api.video'
    verbose_name = '비디오/세미나 관리'

