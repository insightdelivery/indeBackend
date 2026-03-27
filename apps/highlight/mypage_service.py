"""
마이페이지 하이라이트 목록 — 그룹 단위 집계 (wwwMypage_Highlights.md)
- 대표 텍스트: 동일 highlight_group_id 행 중 len(highlight_text) 최대 (SQL MAX 문자열 금지)
- 그룹 시각: MAX(created_at)
"""
from collections import defaultdict

from django.utils import timezone

from sites.admin_api.articles.utils import get_presigned_thumbnail_url as article_presigned_thumbnail

from .models import ArticleHighlight


def _presign_thumb(url):
    if not url:
        return None
    try:
        return article_presigned_thumbnail(url, expires_in=3600) or url
    except Exception:
        return url


def _article_meta(article):
    """삭제·비공개 시에도 카드 표시용 메타."""
    if article is None:
        return '삭제된 콘텐츠입니다', None
    deleted = getattr(article, 'deletedAt', None) is not None
    if deleted or getattr(article, 'status', None) == 'deleted':
        return '삭제된 콘텐츠입니다', None
    title = article.title or ''
    thumb = _presign_thumb((article.thumbnail or '').strip() or None)
    return title, thumb


def _build_groups_for_user(user):
    """
    사용자의 모든 하이라이트 row를 불러와 highlight_group_id 단위로 묶는다.
    Returns: list of dicts with keys used by date/article serializers (+ _sort datetime).
    """
    rows = (
        ArticleHighlight.objects.filter(user=user)
        .select_related('article')
        .order_by('highlight_group_id', 'id')
    )
    by_gid = defaultdict(list)
    for r in rows:
        by_gid[r.highlight_group_id].append(r)

    out = []
    for gid, group_rows in by_gid.items():
        max_created = max(r.created_at for r in group_rows)
        rep_row = max(group_rows, key=lambda r: len((r.highlight_text or '')))
        highlight_text = rep_row.highlight_text or ''
        article = rep_row.article
        aid = article.id if article else rep_row.article_id
        title, thumb = _article_meta(article)

        out.append(
            {
                'highlightGroupId': gid,
                'articleId': aid,
                'highlightText': highlight_text,
                'articleTitle': title,
                'thumbnail': thumb,
                'createdAt': max_created.isoformat(),
                '_sort': max_created,
            }
        )

    out.sort(key=lambda x: x['_sort'], reverse=True)
    return out


def _serialize_item(g):
    return {
        'highlightGroupId': g['highlightGroupId'],
        'articleId': g['articleId'],
        'highlightText': g['highlightText'],
        'articleTitle': g['articleTitle'],
        'thumbnail': g['thumbnail'],
        'createdAt': g['createdAt'],
    }


def build_date_view_result(user):
    """groupType: date — groupKey = YYYY-MM-DD (로컬 타임존 날짜)."""
    groups = _build_groups_for_user(user)
    by_date = defaultdict(list)
    for g in groups:
        dk = timezone.localtime(g['_sort']).date().isoformat()
        by_date[dk].append(g)

    result = []
    for date_key in sorted(by_date.keys(), reverse=True):
        items = by_date[date_key]
        items.sort(key=lambda x: x['_sort'], reverse=True)
        result.append(
            {
                'groupKey': date_key,
                'groupType': 'date',
                'items': [_serialize_item(x) for x in items],
            }
        )
    return result


def build_article_view_result(user):
    """groupType: article — groupKey = str(articleId)."""
    groups = _build_groups_for_user(user)
    by_art = defaultdict(list)
    for g in groups:
        by_art[g['articleId']].append(g)

    article_order = sorted(by_art.keys(), key=lambda aid: max(x['_sort'] for x in by_art[aid]), reverse=True)

    result = []
    for aid in article_order:
        items = by_art[aid]
        items.sort(key=lambda x: x['_sort'], reverse=True)
        result.append(
            {
                'groupKey': str(aid),
                'groupType': 'article',
                'items': [_serialize_item(x) for x in items],
            }
        )
    return result
