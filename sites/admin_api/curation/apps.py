from django.apps import AppConfig


class CurationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sites.admin_api.curation'
    verbose_name = '특집(큐레이션) 콘텐츠'
