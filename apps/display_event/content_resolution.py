"""
contentTypeCode(sysCodeSid) → 콘텐츠 로더 매핑.
검증용 허용 목록이 아니라 '어떤 sid를 어떤 모델에서 로드할지' 연결만 담당.
매핑에 없는 sid → content 없음 (CUSTOM 등).
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from django.db.models import Q

from sites.admin_api.articles.models import Article
from sites.admin_api.articles.utils import get_presigned_thumbnail_url
from sites.admin_api.video.models import Video

# 문서 예시 SID — 신규 타입은 DB에만 추가하고, 로드가 필요하면 여기에 매핑 추가
SID_ARTICLE = "SYS26320B010"
SID_VIDEO = "SYS26320B011"
SID_SEMINAR = "SYS26320B012"


def _article_payload(article: Article) -> dict[str, Any]:
    thumb = article.thumbnail
    if thumb:
        try:
            thumb = get_presigned_thumbnail_url(thumb, expires_in=3600)
        except Exception:
            pass
    return {
        "id": article.id,
        "title": article.title,
        "thumbnail": thumb,
        "subtitle": article.subtitle,
    }


def _video_payload(video: Video) -> dict[str, Any]:
    thumb = video.thumbnail
    if thumb:
        try:
            thumb = get_presigned_thumbnail_url(thumb, expires_in=3600)
        except Exception:
            pass
    return {
        "id": video.id,
        "title": video.title,
        "thumbnail": thumb,
        "subtitle": video.subtitle,
    }


def _load_article(content_id: int) -> Optional[dict]:
    a = (
        Article.objects.filter(id=content_id, deletedAt__isnull=True)
        .filter(Q(status="SYS26209B021") | Q(status="published"))
        .first()
    )
    return _article_payload(a) if a else None


def _load_video(content_id: int) -> Optional[dict]:
    v = Video.objects.filter(
        id=content_id,
        deletedAt__isnull=True,
        contentType="video",
    ).exclude(status="deleted").first()
    return _video_payload(v) if v else None


def _load_seminar(content_id: int) -> Optional[dict]:
    v = Video.objects.filter(
        id=content_id,
        deletedAt__isnull=True,
        contentType="seminar",
    ).exclude(status="deleted").first()
    return _video_payload(v) if v else None


# sid → loader (content_id 필수)
CONTENT_LOADERS: dict[str, Callable[[int], Optional[dict]]] = {
    SID_ARTICLE: _load_article,
    SID_VIDEO: _load_video,
    SID_SEMINAR: _load_seminar,
}


def load_content(content_type_code: str, content_id: Optional[int]) -> Optional[dict]:
    if content_id is None:
        return None
    loader = CONTENT_LOADERS.get(content_type_code)
    if not loader:
        return None
    return loader(int(content_id))
