"""
관리자 비디오·세미나 목록용 content_question / content_question_answer 집계 annotate.
"""
from django.db.models import Case, Count, IntegerField, OuterRef, Subquery, Value, When
from django.db.models.functions import Coalesce
from django.db.models.query import QuerySet

from apps.content_question.models import ContentQuestion, ContentQuestionAnswer


def annotate_video_question_counts(queryset: QuerySet) -> QuerySet:
    """
    Video.contentType 이 video → VIDEO, seminar → SEMINAR 질문·답변 집계를 붙인다.
    """
    sq_reg_video = (
        ContentQuestion.objects.filter(
            content_type=ContentQuestion.CONTENT_TYPE_VIDEO,
            content_id=OuterRef("pk"),
        )
        .values("content_id")
        .annotate(_cnt=Count("question_id"))
        .values("_cnt")[:1]
    )
    sq_reg_seminar = (
        ContentQuestion.objects.filter(
            content_type=ContentQuestion.CONTENT_TYPE_SEMINAR,
            content_id=OuterRef("pk"),
        )
        .values("content_id")
        .annotate(_cnt=Count("question_id"))
        .values("_cnt")[:1]
    )
    sq_ans_video = (
        ContentQuestionAnswer.objects.filter(
            content_type=ContentQuestionAnswer.CONTENT_TYPE_VIDEO,
            content_id=OuterRef("pk"),
        )
        .values("content_id")
        .annotate(_cnt=Count("question_id", distinct=True))
        .values("_cnt")[:1]
    )
    sq_ans_seminar = (
        ContentQuestionAnswer.objects.filter(
            content_type=ContentQuestionAnswer.CONTENT_TYPE_SEMINAR,
            content_id=OuterRef("pk"),
        )
        .values("content_id")
        .annotate(_cnt=Count("question_id", distinct=True))
        .values("_cnt")[:1]
    )
    return queryset.annotate(
        applied_question_count=Case(
            When(
                contentType="video",
                then=Coalesce(Subquery(sq_reg_video, output_field=IntegerField()), Value(0)),
            ),
            When(
                contentType="seminar",
                then=Coalesce(Subquery(sq_reg_seminar, output_field=IntegerField()), Value(0)),
            ),
            default=Value(0),
            output_field=IntegerField(),
        ),
        answered_question_count=Case(
            When(
                contentType="video",
                then=Coalesce(Subquery(sq_ans_video, output_field=IntegerField()), Value(0)),
            ),
            When(
                contentType="seminar",
                then=Coalesce(Subquery(sq_ans_seminar, output_field=IntegerField()), Value(0)),
            ),
            default=Value(0),
            output_field=IntegerField(),
        ),
    )
