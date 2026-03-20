"""공개 비디오 API (frontend_www)"""
from django.urls import path
from sites.public_api.video_views import PublicVideoListView

urlpatterns = [
    path("", PublicVideoListView.as_view(), name="public_video_list"),
]
