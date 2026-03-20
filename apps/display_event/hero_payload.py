"""Hero API 응답: title / imageUrl / subtitle 서버 최종 합성, linkUrl 규칙."""

from __future__ import annotations

from typing import Any, Optional

from .link_url import normalize_link_url
from .models import DisplayEvent


def build_hero_item(
    event: DisplayEvent,
    content: Optional[dict],
    *,
    include_admin_fields: bool = False,
) -> dict[str, Any]:
    # 표시 필드 (서버 확정)
    title = (event.title or "").strip() if event.title else ""
    if not title and content:
        title = (content.get("title") or "").strip() or ""
    subtitle = (event.subtitle or "").strip() if event.subtitle else None
    if subtitle == "":
        subtitle = None
    image_url = (event.image_url or "").strip() if event.image_url else ""
    if not image_url and content:
        image_url = (content.get("thumbnail") or "").strip() or ""
    if image_url == "":
        image_url = None

    # linkUrl: contentId 있으면 무조건 null
    out_link = None
    if event.content_id is None:
        out_link = normalize_link_url(event.link_url)

    out: dict[str, Any] = {
        "displayEventId": event.id,
        "eventTypeCode": event.event_type_code,
        "contentTypeCode": event.content_type_code,
        "contentId": event.content_id,
        "title": title or None,
        "subtitle": subtitle,
        "imageUrl": image_url,
        "linkUrl": out_link,
        "content": content,
    }
    if include_admin_fields:
        out["displayOrder"] = event.display_order
        out["isActive"] = event.is_active
        out["startAt"] = event.start_at.isoformat() if event.start_at else None
        out["endAt"] = event.end_at.isoformat() if event.end_at else None
    return out
