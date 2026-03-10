"""
관리자 API URL: /content/questions/
"""
from django.urls import path
from . import admin_views

urlpatterns = [
    path('', admin_views.AdminContentQuestionListView.as_view(), name='admin_content_question_list'),
    path('<int:question_id>/', admin_views.AdminContentQuestionDetailView.as_view(), name='admin_content_question_detail'),
]
