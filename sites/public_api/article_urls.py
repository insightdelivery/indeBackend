"""
공개 아티클 API URL (frontend_www)
"""
from django.urls import path
from sites.public_api.article_views import PublicArticleListView, PublicArticleDetailView

urlpatterns = [
    path('', PublicArticleListView.as_view(), name='public_article_list'),
    path('<int:id>/', PublicArticleDetailView.as_view(), name='public_article_detail'),
]
