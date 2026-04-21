"""
통합 공개 검색 API (frontend_www)
GET /api/search/?q= — 아티클 / 비디오 / 세미나 분리 응답
"""
import json
import logging

from django.db.models import Case, IntegerField, Q, Value, When
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import SysCodeManager
from core.utils import create_error_response, create_success_response
from sites.admin_api.articles.models import Article
from sites.admin_api.content_publish_syscodes import STATUS_PUBLISHED
from sites.admin_api.articles.serializers import ArticleListSerializer
from sites.admin_api.articles.utils import get_presigned_thumbnail_url
from sites.admin_api.video.models import Video
from sites.admin_api.video.serializers import VideoListSerializer
from sites.admin_api.video.utils import get_presigned_thumbnail_url as video_presign_thumb

logger = logging.getLogger(__name__)

SEARCH_LIMIT = 80


def _normalize_tags(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(t).strip() for t in value if str(t).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(t).strip() for t in parsed if str(t).strip()]
        except (json.JSONDecodeError, TypeError):
            pass
    return []


def _category_q_for_term(term: str) -> Q:
    """category 컬럼은 sysCodeSid 문자열 — SID 부분 일치 + 시스코드 표시명 매칭 시 해당 SID."""
    q = Q(category__icontains=term)
    sids = SysCodeManager.objects.filter(sysCodeName__icontains=term).values_list(
        "sysCodeSid", flat=True
    )
    sid_list = [s for s in sids if s]
    if sid_list:
        q |= Q(category__in=sid_list)
    return q


def _article_search_q(term: str) -> Q:
    return (
        Q(title__icontains=term)
        | Q(subtitle__icontains=term)
        | Q(content__icontains=term)
        | Q(author__icontains=term)
        | Q(tags__icontains=term)
        | _category_q_for_term(term)
    )


def _video_search_q(term: str) -> Q:
    return (
        Q(title__icontains=term)
        | Q(subtitle__icontains=term)
        | Q(body__icontains=term)
        | Q(tags__icontains=term)
        | _category_q_for_term(term)
        | Q(speaker__icontains=term)
        | Q(speakerAffiliation__icontains=term)
        | Q(editor__icontains=term)
        | Q(director__icontains=term)
    )


def _article_priority_case(term: str) -> Case:
    cat_q = _category_q_for_term(term)
    tags_q = Q(tags__icontains=term)
    return Case(
        When(Q(title__icontains=term), then=Value(1)),
        When(Q(subtitle__icontains=term), then=Value(2)),
        When(cat_q, then=Value(3)),
        When(tags_q, then=Value(4)),
        When(Q(content__icontains=term), then=Value(5)),
        When(Q(author__icontains=term), then=Value(6)),
        default=Value(999),
        output_field=IntegerField(),
    )


def _video_priority_case(term: str) -> Case:
    cat_q = _category_q_for_term(term)
    tags_q = Q(tags__icontains=term)
    meta_q = (
        Q(speaker__icontains=term)
        | Q(speakerAffiliation__icontains=term)
        | Q(editor__icontains=term)
        | Q(director__icontains=term)
    )
    return Case(
        When(Q(title__icontains=term), then=Value(1)),
        When(Q(subtitle__icontains=term), then=Value(2)),
        When(cat_q, then=Value(3)),
        When(tags_q, then=Value(4)),
        When(Q(body__icontains=term), then=Value(5)),
        When(meta_q, then=Value(6)),
        default=Value(999),
        output_field=IntegerField(),
    )


class PublicUnifiedSearchView(APIView):
    """
    GET /api/search/?q=
    Result: { article: ContentItem[], video: ContentItem[], seminar: ContentItem[] }
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            q = (request.query_params.get("q") or "").strip()
            if not q:
                empty = {"article": [], "video": [], "seminar": []}
                return Response(
                    create_success_response(empty, "검색 결과 없음"),
                    status=status.HTTP_200_OK,
                )

            article_qs = (
                Article.objects.filter(deletedAt__isnull=True)
                .filter(Q(status=STATUS_PUBLISHED))
                .filter(_article_search_q(q))
                .annotate(priority=_article_priority_case(q))
                .order_by("priority", "-createdAt")[:SEARCH_LIMIT]
            )

            video_base = Video.objects.filter(
                deletedAt__isnull=True,
                status=STATUS_PUBLISHED,
            )

            video_qs = (
                video_base.filter(contentType="video")
                .filter(_video_search_q(q))
                .annotate(priority=_video_priority_case(q))
                .order_by("priority", "-createdAt")[:SEARCH_LIMIT]
            )

            seminar_qs = (
                video_base.filter(contentType="seminar")
                .filter(_video_search_q(q))
                .annotate(priority=_video_priority_case(q))
                .order_by("priority", "-createdAt")[:SEARCH_LIMIT]
            )

            article_items = []
            for obj in article_qs:
                data = ArticleListSerializer(obj).data
                thumb = data.get("thumbnail") or ""
                if thumb:
                    thumb = get_presigned_thumbnail_url(thumb, expires_in=3600) or ""
                article_items.append(
                    {
                        "id": data["id"],
                        "title": data.get("title") or "",
                        "subtitle": data.get("subtitle") or "",
                        "thumbnail": thumb,
                        "category": data.get("category") or "",
                        "writer": data.get("author") or "",
                        "tags": _normalize_tags(data.get("tags")),
                        "priority": int(getattr(obj, "priority", 999)),
                    }
                )

            def _video_rows(queryset):
                rows = []
                for obj in queryset:
                    data = VideoListSerializer(obj).data
                    thumb = data.get("thumbnail") or ""
                    if thumb:
                        thumb = video_presign_thumb(thumb, expires_in=3600) or ""
                    writer = (data.get("editor") or data.get("speaker") or "").strip()
                    rows.append(
                        {
                            "id": data["id"],
                            "title": data.get("title") or "",
                            "subtitle": data.get("subtitle") or "",
                            "thumbnail": thumb,
                            "category": data.get("category") or "",
                            "writer": writer,
                            "tags": _normalize_tags(obj.tags),
                            "priority": int(getattr(obj, "priority", 999)),
                        }
                    )
                return rows

            result = {
                "article": article_items,
                "video": _video_rows(video_qs),
                "seminar": _video_rows(seminar_qs),
            }

            return Response(
                create_success_response(result, "통합 검색 성공"),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("통합 검색 실패: %s", e)
            return Response(
                create_error_response(f"통합 검색 실패: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
