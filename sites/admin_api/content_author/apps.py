"""
콘텐츠 저자(Content Author) 앱 설정
"""
from django.apps import AppConfig


class ContentAuthorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sites.admin_api.content_author'
    verbose_name = '콘텐츠 저자 관리'
