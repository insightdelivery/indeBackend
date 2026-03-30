"""
공개/사용자 API URL: /api/content/
"""
from django.urls import path
from . import public_views

urlpatterns = [
    path(
        'my-answered-contents',
        public_views.ContentMyAnsweredContentsListView.as_view(),
        name='content_my_answered_contents',
    ),
    path(
        'my-answered-contents/',
        public_views.ContentMyAnsweredContentsListView.as_view(),
        name='content_my_answered_contents_slash',
    ),
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
    path(
        '<str:content_type>/<int:content_id>/my-answers',
        public_views.ContentQuestionMyAnswersView.as_view(),
        name='content_my_answers',
    ),
    path(
        '<str:content_type>/<int:content_id>/my-answers/',
        public_views.ContentQuestionMyAnswersView.as_view(),
        name='content_my_answers_slash',
    ),
    path(
        'question-answer/<int:answer_id>',
        public_views.ContentQuestionAnswerDetailView.as_view(),
        name='content_question_answer_detail',
    ),
    path(
        'question-answer/<int:answer_id>/',
        public_views.ContentQuestionAnswerDetailView.as_view(),
        name='content_question_answer_detail_slash',
    ),
    path('question-answer', public_views.ContentQuestionAnswerCreateView.as_view(), name='content_question_answer'),
    path('question-answer/', public_views.ContentQuestionAnswerCreateView.as_view(), name='content_question_answer_slash'),
]
