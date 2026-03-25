"""
공개/사용자 API URL: /api/content/
"""
from django.urls import path
from . import public_views

urlpatterns = [
    path(
        '<str:content_type>/<int:content_id>/questions',
        public_views.ContentQuestionListView.as_view(),
        name='content_questions',
    ),
    path(
        '<str:content_type>/<int:content_id>/questions/',
        public_views.ContentQuestionListView.as_view(),
        name='content_questions_slash',
    ),
    path('question-answer', public_views.ContentQuestionAnswerCreateView.as_view(), name='content_question_answer'),
    path('question-answer/', public_views.ContentQuestionAnswerCreateView.as_view(), name='content_question_answer_slash'),
]
