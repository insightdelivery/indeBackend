from django.urls import path

from . import views


urlpatterns = [
    path("kakao-templates", views.KakaoTemplateListCreateView.as_view()),
    path("kakao-templates/<int:template_id>", views.KakaoTemplateDetailView.as_view()),
    path("batches", views.MessageBatchListCreateView.as_view()),
    path("batches/<int:batch_id>", views.MessageBatchDetailView.as_view()),
    path("batches/<int:batch_id>/cancel", views.MessageBatchCancelView.as_view()),
    path("batches/<int:batch_id>/resend-failed", views.MessageBatchResendFailedView.as_view()),
    path("sender-numbers", views.MessageSenderNumberListCreateView.as_view()),
    path("sender-numbers/<int:sender_id>", views.MessageSenderNumberDeleteView.as_view()),
    path("sender-emails", views.MessageSenderEmailListCreateView.as_view()),
    path("sender-emails/<int:sender_id>", views.MessageSenderEmailDeleteView.as_view()),
    path("templates", views.MessageTemplateListCreateView.as_view()),
    path("templates/<int:template_id>", views.MessageTemplateDetailView.as_view()),
    path("remain", views.AligoRemainView.as_view()),
    path("batches/<int:batch_id>/sync-result", views.MessageBatchSyncResultView.as_view()),
]
