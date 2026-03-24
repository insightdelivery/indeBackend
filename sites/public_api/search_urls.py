"""공개 통합 검색 API (frontend_www)"""
from django.urls import path

from sites.public_api.search_views import PublicUnifiedSearchView

urlpatterns = [
    path("", PublicUnifiedSearchView.as_view(), name="public_unified_search"),
]
