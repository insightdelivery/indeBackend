"""
비디오/세미나 엑셀 등: content_question 기준 질문·답변 집계.
"""
from __future__ import annotations

from django.db.models import Count

from apps.content_question.models import ContentQuestion, ContentQuestionAnswer


def _content_question_type_for_video_row(content_type_raw: str) -> str:
    if (content_type_raw or "").strip().lower() == "video":
        return ContentQuestion.CONTENT_TYPE_VIDEO
    return ContentQuestion.CONTENT_TYPE_SEMINAR


def video_seminar_question_answer_pairs(video_rows) -> dict[int, tuple[int, int]]:
    """
    video_rows: Video 모델 인스턴스 iterable (id, contentType 사용).
    반환: { video_pk: (answered_distinct_question_count, registered_question_count) }
    """
    rows = list(video_rows)
    if not rows:
        return {}

    ids = [v.id for v in rows]
    totals: dict[tuple[int, str], int] = {}
    for row in (
        ContentQuestion.objects.filter(content_id__in=ids)
        .values("content_id", "content_type")
        .annotate(c=Count("question_id"))
    ):
        totals[(row["content_id"], row["content_type"])] = int(row["c"] or 0)

    answered: dict[tuple[int, str], int] = {}
    for row in (
        ContentQuestionAnswer.objects.filter(content_id__in=ids)
        .values("content_id", "content_type")
        .annotate(c=Count("question_id", distinct=True))
    ):
        answered[(row["content_id"], row["content_type"])] = int(row["c"] or 0)

    out: dict[int, tuple[int, int]] = {}
    for v in rows:
        ct = _content_question_type_for_video_row(getattr(v, "contentType", "") or "")
        key = (v.id, ct)
        out[v.id] = (answered.get(key, 0), totals.get(key, 0))
    return out
