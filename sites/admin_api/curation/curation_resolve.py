"""
원본 콘텐츠 조회(참조) — curationContentPlan.md §2-1
"""
from __future__ import annotations

import re

from core.models import SysCodeManager
from core.s3_storage import get_s3_storage
from sites.admin_api.articles.models import Article
from sites.admin_api.articles.utils import get_presigned_thumbnail_url as presign_article_thumbnail
from sites.admin_api.video.models import Video
from sites.admin_api.video.utils import get_presigned_thumbnail_url as presign_video_thumbnail

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


def _presign_curation_thumbnail(raw: str | None, content_type: str) -> str:
    """
    메인 큐레이션 카드용 썸네일 — 공개 article/video API와 동일하게 S3는 presigned URL로 내려준다.
    DB에 객체 키만 있는 경우(article/…, video/…)는 키로 직접 presign.
    """
    if not raw or not str(raw).strip():
        return ''
    u = str(raw).strip()
    if u.startswith('data:image'):
        return u
    if u.startswith('article/') or u.startswith('video/'):
        try:
            signed = get_s3_storage().get_file_url(u, expires_in=3600, force_presigned=True)
            return (signed or u).strip()
        except Exception:
            return u
    if content_type == CurationItem.ContentType.ARTICLE:
        out = presign_article_thumbnail(u, expires_in=3600)
    elif content_type in (CurationItem.ContentType.VIDEO, CurationItem.ContentType.SEMINAR):
        out = presign_video_thumbnail(u, expires_in=3600)
    else:
        out = None
    return ((out or u) or '').strip()


def build_public_card(item: CurationItem, resolved: dict) -> dict:
    """메인 §10 카드 필드. id는 curation_item PK(클라이언트 key용)."""
    orig_title = resolved.get('displayTitle') or ''
    title = effective_display_title(item.custom_title, orig_title)
    raw_thumb = resolved.get('thumbnail') or ''
    thumb = _presign_curation_thumbnail(raw_thumb, item.content_type)
    return {
        'id': item.id,
        'title': title,
        'thumbnail': thumb,
        'categoryName': resolved.get('categoryName') or '',
        'summary': resolved.get('summary') or '',
        'contentType': item.content_type,
        'contentCode': int(item.content_code),
    }
