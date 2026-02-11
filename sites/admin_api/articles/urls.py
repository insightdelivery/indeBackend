"""
아티클 API URL 설정
"""
from django.urls import path
from sites.admin_api.articles.views import (
    ArticleListView,
    ArticleDetailView,
    ArticleCreateView,
    ArticleUpdateView,
    ArticleDeleteView,
    ArticleBatchDeleteView,
    ArticleBatchStatusView,
    ArticleRestoreView,
    ArticleHardDeleteView,
    ArticleExportView,
)

app_name = 'articles'

urlpatterns = [
    # 아티클 목록 조회
    path('list/', ArticleListView.as_view(), name='article_list'),
    path('list', ArticleListView.as_view(), name='article_list_no_slash'),
    
    # 아티클 생성
    path('create/', ArticleCreateView.as_view(), name='article_create'),
    path('create', ArticleCreateView.as_view(), name='article_create_no_slash'),
    
    # 아티클 일괄 삭제
    path('batch-delete/', ArticleBatchDeleteView.as_view(), name='article_batch_delete'),
    path('batch-delete', ArticleBatchDeleteView.as_view(), name='article_batch_delete_no_slash'),
    
    # 아티클 상태 일괄 변경
    path('batch-status/', ArticleBatchStatusView.as_view(), name='article_batch_status'),
    path('batch-status', ArticleBatchStatusView.as_view(), name='article_batch_status_no_slash'),
    
    # 아티클 엑셀 다운로드
    path('export/', ArticleExportView.as_view(), name='article_export'),
    path('export', ArticleExportView.as_view(), name='article_export_no_slash'),
    
    # 아티클 복구
    path('<int:id>/restore/', ArticleRestoreView.as_view(), name='article_restore'),
    path('<int:id>/restore', ArticleRestoreView.as_view(), name='article_restore_no_slash'),
    
    # 아티클 영구 삭제
    path('<int:id>/hard-delete/', ArticleHardDeleteView.as_view(), name='article_hard_delete'),
    path('<int:id>/hard-delete', ArticleHardDeleteView.as_view(), name='article_hard_delete_no_slash'),
    
    # 아티클 상세 조회, 수정, 삭제 (GET, PUT, DELETE)
    path('<int:id>/', ArticleDetailView.as_view(), name='article_detail'),
    path('<int:id>', ArticleDetailView.as_view(), name='article_detail_no_slash'),
]

