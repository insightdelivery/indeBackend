"""
관리자 아티클 목록 등에서 사용하는 질문·답변 집계 annotate.
"""
from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.db.models.query import QuerySet

from apps.content_question.models import ContentQuestion, ContentQuestionAnswer


def annotate_article_question_counts(queryset: QuerySet) -> QuerySet:
    """
    등록 질문 수(content_question)와 답변이 1건 이상 있는 질문 수(distinct question_id)를 붙인다.
    """
    sq_registered = (
        ContentQuestion.objects.filter(
            content_type=ContentQuestion.CONTENT_TYPE_ARTICLE,
            content_id=OuterRef('pk'),
        )
        .values('content_id')
        .annotate(_cnt=Count('question_id'))
        .values('_cnt')[:1]
    )
    sq_answered = (
        ContentQuestionAnswer.objects.filter(
            content_type=ContentQuestionAnswer.CONTENT_TYPE_ARTICLE,
            content_id=OuterRef('pk'),
        )
        .values('content_id')
        .annotate(_cnt=Count('question_id', distinct=True))
        .values('_cnt')[:1]
    )
    return queryset.annotate(
        applied_question_count=Coalesce(
            Subquery(sq_registered, output_field=IntegerField()),
            Value(0),
        ),
        answered_question_count=Coalesce(
            Subquery(sq_answered, output_field=IntegerField()),
            Value(0),
        ),
    )
