"""
비디오/세미나 API URL 설정
"""
from django.urls import path
from sites.admin_api.video.views import (
    VideoListView,
    VideoDetailView,
    VideoCreateView,
    VideoBatchDeleteView,
    VideoBatchStatusView,
    VideoRestoreView,
    VideoHardDeleteView,
    VideoUploadView,
    VideoStreamInfoView,
)
from sites.admin_api.video.tus_views import TUSUploadView, TUSCompleteView

app_name = 'video'

urlpatterns = [
    # 비디오/세미나 목록 조회
    path('list/', VideoListView.as_view(), name='video_list'),
    path('list', VideoListView.as_view(), name='video_list_no_slash'),
    
    # 비디오/세미나 생성
    path('create/', VideoCreateView.as_view(), name='video_create'),
    path('create', VideoCreateView.as_view(), name='video_create_no_slash'),
    
    # 비디오 파일 업로드 (Cloudflare Stream) - 기존 방식 (하위 호환성)
    path('upload/', VideoUploadView.as_view(), name='video_upload'),
    path('upload', VideoUploadView.as_view(), name='video_upload_no_slash'),
    
    # TUS 업로드 엔드포인트
    path('upload/tus/', TUSUploadView.as_view(), name='tus_upload_create'),
    path('upload/tus', TUSUploadView.as_view(), name='tus_upload_create_no_slash'),
    path('upload/tus/<str:upload_id>/', TUSUploadView.as_view(), name='tus_upload'),
    path('upload/tus/<str:upload_id>', TUSUploadView.as_view(), name='tus_upload_no_slash'),
    path('upload/tus/<str:upload_id>/complete/', TUSCompleteView.as_view(), name='tus_upload_complete'),
    path('upload/tus/<str:upload_id>/complete', TUSCompleteView.as_view(), name='tus_upload_complete_no_slash'),
    
    # Cloudflare Stream 비디오 정보 조회
    path('stream/<str:videoStreamId>/info/', VideoStreamInfoView.as_view(), name='video_stream_info'),
    path('stream/<str:videoStreamId>/info', VideoStreamInfoView.as_view(), name='video_stream_info_no_slash'),
    
    # 비디오/세미나 일괄 삭제
    path('batch-delete/', VideoBatchDeleteView.as_view(), name='video_batch_delete'),
    path('batch-delete', VideoBatchDeleteView.as_view(), name='video_batch_delete_no_slash'),
    
    # 비디오/세미나 상태 일괄 변경
    path('batch-status/', VideoBatchStatusView.as_view(), name='video_batch_status'),
    path('batch-status', VideoBatchStatusView.as_view(), name='video_batch_status_no_slash'),
    
    # 비디오/세미나 복구
    path('<int:id>/restore/', VideoRestoreView.as_view(), name='video_restore'),
    path('<int:id>/restore', VideoRestoreView.as_view(), name='video_restore_no_slash'),
    
    # 비디오/세미나 영구 삭제
    path('<int:id>/hard-delete/', VideoHardDeleteView.as_view(), name='video_hard_delete'),
    path('<int:id>/hard-delete', VideoHardDeleteView.as_view(), name='video_hard_delete_no_slash'),
    
    # 비디오/세미나 상세 조회, 수정, 삭제 (GET, PUT, DELETE)
    path('<int:id>/', VideoDetailView.as_view(), name='video_detail'),
    path('<int:id>', VideoDetailView.as_view(), name='video_detail_no_slash'),
]

