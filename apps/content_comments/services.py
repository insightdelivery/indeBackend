from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Tuple

from django.db import transaction
from django.db.models import F

from sites.admin_api.articles.models import Article
from sites.admin_api.video.models import Video

ContentType = Literal["ARTICLE", "VIDEO", "SEMINAR"]


@dataclass(frozen=True)
class ContentGate:
    exists: bool
    allow_comment: bool
    comment_count: int


def validate_content_type(value: str) -> Optional[ContentType]:
    v = (value or "").strip().upper()
    if v in ("ARTICLE", "VIDEO", "SEMINAR"):
        return v  # type: ignore[return-value]
    return None


def get_content_gate(content_type: ContentType, content_id: int) -> ContentGate:
    """
    allowComment/commentCount 확인용.
    - ARTICLE: deleted 제외
    - VIDEO/SEMINAR: deleted 제외 + contentType 일치
    """
    if content_type == "ARTICLE":
        a = Article.objects.filter(id=content_id, deletedAt__isnull=True).only("id", "commentCount").first()
        if not a:
            return ContentGate(False, False, 0)
        allow = bool(getattr(a, "allowComment", True))
        return ContentGate(True, allow, int(a.commentCount or 0))

    v = Video.objects.filter(id=content_id, deletedAt__isnull=True).only("id", "contentType", "allowComment", "commentCount").first()
    if not v:
        return ContentGate(False, False, 0)
    if content_type == "VIDEO" and v.contentType != "video":
        return ContentGate(False, False, 0)
    if content_type == "SEMINAR" and v.contentType != "seminar":
        return ContentGate(False, False, 0)
    return ContentGate(True, bool(v.allowComment), int(v.commentCount or 0))


@transaction.atomic
def bump_comment_count(content_type: ContentType, content_id: int, delta: int) -> None:
    """
    콘텐츠별 댓글 수(깊이 1 루트 댓글만)를 F()로 증감.
    대댓글(depth 2)·관리자 대댓글 경로에서는 호출하지 않는다.
    """
    if delta == 0:
        return
    if content_type == "ARTICLE":
        Article.objects.filter(id=content_id).update(commentCount=F("commentCount") + delta)
        return
    Video.objects.filter(id=content_id).update(commentCount=F("commentCount") + delta)

