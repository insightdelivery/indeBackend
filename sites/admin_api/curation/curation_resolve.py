"""
원본 콘텐츠 조회(참조) — curationContentPlan.md §2-1
"""
from __future__ import annotations

import re

from core.models import SysCodeManager
from sites.admin_api.articles.models import Article
from sites.admin_api.video.models import Video

from .models import CurationItem


def _plain_text(text: str | None, max_len: int = 220) -> str:
    if not text:
        return ''
    t = re.sub(r'<[^>]+>', '', str(text))
    t = ' '.join(t.split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + '…'


def category_label(sys_code_sid: str | None) -> str:
    if not sys_code_sid:
        return ''
    row = SysCodeManager.objects.filter(sysCodeSid=sys_code_sid, sysCodeUse='Y').first()
    return row.sysCodeName if row else sys_code_sid


def resolve_article(content_code: int) -> dict | None:
    try:
        a = Article.objects.get(pk=content_code)
    except Article.DoesNotExist:
        return None
    if a.deletedAt is not None:
        return None
    summary = (a.subtitle or '').strip() or _plain_text(a.content)
    return {
        'displayTitle': a.title,
        'thumbnail': (a.thumbnail or '').strip(),
        'summary': summary,
        'categoryName': category_label(a.category),
    }


def resolve_video(content_code: int, expect_content_type: str) -> dict | None:
    """expect_content_type: 'video' | 'seminar' (Video.contentType DB 값)."""
    try:
        v = Video.objects.get(pk=content_code)
    except Video.DoesNotExist:
        return None
    if v.deletedAt is not None:
        return None
    if (v.contentType or '').lower() != expect_content_type:
        return None
    summary = (v.subtitle or '').strip() or _plain_text(v.body)
    return {
        'displayTitle': v.title,
        'thumbnail': (v.thumbnail or '').strip(),
        'summary': summary,
        'categoryName': category_label(v.category),
    }


def resolve_curation_target(content_type: str, content_code: int) -> dict | None:
    if content_type == CurationItem.ContentType.ARTICLE:
        return resolve_article(content_code)
    if content_type == CurationItem.ContentType.VIDEO:
        return resolve_video(content_code, 'video')
    if content_type == CurationItem.ContentType.SEMINAR:
        return resolve_video(content_code, 'seminar')
    return None


def effective_display_title(custom_title: str | None, original_title: str) -> str:
    t = (custom_title or '').strip()
    return t if t else (original_title or '')


def build_public_card(item: CurationItem, resolved: dict) -> dict:
    """메인 §10 카드 필드. id는 curation_item PK(클라이언트 key용)."""
    orig_title = resolved.get('displayTitle') or ''
    title = effective_display_title(item.custom_title, orig_title)
    return {
        'id': item.id,
        'title': title,
        'thumbnail': resolved.get('thumbnail') or '',
        'categoryName': resolved.get('categoryName') or '',
        'summary': resolved.get('summary') or '',
        'contentType': item.content_type,
        'contentCode': int(item.content_code),
    }
