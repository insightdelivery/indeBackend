"""
아티클 앱 설정
"""
from django.apps import AppConfig


class ArticlesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sites.admin_api.articles'
    verbose_name = '아티클 관리'

