from django.urls import path

from apps.content_comments import public_views


urlpatterns = [
    path("comments", public_views.PublicCommentListCreateView.as_view(), name="public_comments"),
    path("comments/", public_views.PublicCommentListCreateView.as_view(), name="public_comments_slash"),
    path("comments/<int:comment_id>", public_views.PublicCommentDetailView.as_view(), name="public_comment_detail"),
    path("comments/<int:comment_id>/", public_views.PublicCommentDetailView.as_view(), name="public_comment_detail_slash"),
]

