"""공개 비디오 API (frontend_www)"""
from django.urls import path
from sites.public_api.video_views import PublicVideoListView, PublicVideoDetailView

urlpatterns = [
    path("<int:id>", PublicVideoDetailView.as_view(), name="public_video_detail"),
    path("<int:id>/", PublicVideoDetailView.as_view(), name="public_video_detail_slash"),
    path("", PublicVideoListView.as_view(), name="public_video_list"),
]
