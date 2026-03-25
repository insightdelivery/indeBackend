"""
파일 관리 API URL 설정
"""
from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    path('upload', views.FileUploadView.as_view(), name='file_upload'),
    path('upload/', views.FileUploadView.as_view(), name='file_upload_slash'),
    path('delete', views.FileDeleteView.as_view(), name='file_delete'),
    path('delete/', views.FileDeleteView.as_view(), name='file_delete_slash'),
    path('info', views.FileInfoView.as_view(), name='file_info'),
    path('info/', views.FileInfoView.as_view(), name='file_info_slash'),
    path('list', views.FileListView.as_view(), name='file_list'),
    path('list/', views.FileListView.as_view(), name='file_list_slash'),
]

