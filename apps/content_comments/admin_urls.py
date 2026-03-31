from django.urls import path

from apps.content_comments import admin_views


urlpatterns = [
    path("comments", admin_views.AdminCommentListByContentView.as_view(), name="admin_comments_by_content"),
    path("comments/", admin_views.AdminCommentListByContentView.as_view(), name="admin_comments_by_content_slash"),
    path("comments/<int:comment_id>", admin_views.AdminCommentDetailView.as_view(), name="admin_comment_detail"),
    path("comments/<int:comment_id>/", admin_views.AdminCommentDetailView.as_view(), name="admin_comment_detail_slash"),
]

