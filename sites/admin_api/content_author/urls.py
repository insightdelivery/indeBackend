"""
콘텐츠 저자 API URL 설정
"""
from django.urls import path
from .views import (
    AuthorListView,
    AuthorCreateView,
    AuthorDetailView,
    AuthorsByContentTypeView,
)

app_name = 'content_author'

urlpatterns = [
    path('list/', AuthorListView.as_view(), name='author_list'),
    path('list', AuthorListView.as_view(), name='author_list_no_slash'),
    path('create/', AuthorCreateView.as_view(), name='author_create'),
    path('create', AuthorCreateView.as_view(), name='author_create_no_slash'),
    path('by-content-type/', AuthorsByContentTypeView.as_view(), name='authors_by_content_type'),
    path('by-content-type', AuthorsByContentTypeView.as_view(), name='authors_by_content_type_no_slash'),
    path('<int:id>/', AuthorDetailView.as_view(), name='author_detail'),
    path('<int:id>', AuthorDetailView.as_view(), name='author_detail_no_slash'),
]
