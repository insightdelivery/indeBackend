"""
일 1회 콘텐츠 랭킹 캐시 갱신 (schedulerContentPlan.md)
- publicUserActivityLog 집계 → content_ranking_cache, 트랜잭션 단위 삭제 후 재삽입
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Tuple

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from sites.public_api.models import ContentRankingCache

ARTICLE = 'ARTICLE'
HOT = ContentRankingCache.RANKING_HOT
SHARE = ContentRankingCache.RANKING_SHARE


def _published_article_codes_recent_first() -> List[str]:
    from sites.admin_api.articles.models import Article

    qs = (
        Article.objects.filter(deletedAt__isnull=True)
        .filter(Q(status='SYS26209B021') | Q(status='published'))
        .order_by('-createdAt')
    )
    return [str(pk) for pk in qs.values_list('id', flat=True)]


def _to_float(v) -> float:
    if v is None:
        return 0.0
    return float(v)


def _fill_to_three(ranked: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
    """집계 상위 + 최근 발행 아티클로 3건(결정적, 랜덤 없음)."""
    need = 3
    seen = {code for code, _ in ranked}
    out: List[Tuple[str, float]] = list(ranked[:need])
    for code in _published_article_codes_recent_first():
        if len(out) >= need:
            break
        if code in seen:
            continue
        seen.add(code)
        out.append((code, 0.0))
    return out[:need]


def _fetch_hot_scores(since: datetime) -> List[Tuple[str, float]]:
    sql = """
        SELECT contentCode,
            (
                (COALESCE(AVG(CASE WHEN activityType = 'RATING' THEN ratingValue END), 0) * 5)
                + (SUM(CASE WHEN activityType = 'BOOKMARK' THEN 1 ELSE 0 END) * 3)
                + (SUM(CASE WHEN activityType = 'VIEW' THEN viewCount ELSE 0 END) * 1)
            ) AS score
        FROM publicUserActivityLog
        WHERE contentType = 'ARTICLE'
          AND regDateTime >= %s
        GROUP BY contentCode
        ORDER BY score DESC, contentCode DESC
        LIMIT 3
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [since])
        return [(row[0], _to_float(row[1])) for row in cursor.fetchall()]


def _fetch_share_scores(since: datetime) -> List[Tuple[str, float]]:
    """VIEW와 동일하게 일별 uniq_view 행당 viewCount 합산 → 실제 공유 횟수."""
    sql = """
        SELECT contentCode, COALESCE(SUM(viewCount), 0) AS score
        FROM publicUserActivityLog
        WHERE contentType = 'ARTICLE'
          AND activityType = 'SHARE'
          AND regDateTime >= %s
        GROUP BY contentCode
        ORDER BY score DESC, contentCode DESC
        LIMIT 3
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [since])
        return [(row[0], _to_float(row[1])) for row in cursor.fetchall()]


def _bulk_insert(
    ranking_type: str,
    rows: List[Tuple[str, float]],
    base_date: date,
) -> int:
    objs = [
        ContentRankingCache(
            ranking_type=ranking_type,
            content_type=ARTICLE,
            content_code=code,
            score=score,
            rank_order=i,
            base_date=base_date,
        )
        for i, (code, score) in enumerate(rows, start=1)
    ]
    ContentRankingCache.objects.bulk_create(objs)
    return len(objs)


def run_content_ranking_refresh(base_date: date | None = None) -> int:
    """
    당일 base_date 캐시를 비우고 HOT·SHARE 각 3건을 다시 적재한다.
    Returns: 삽입된 총 행 수.
    """
    if base_date is None:
        base_date = timezone.localdate()

    now = timezone.now()
    hot_since = now - timedelta(days=14)
    share_since = now - timedelta(days=30)

    inserted = 0
    with transaction.atomic():
        ContentRankingCache.objects.filter(base_date=base_date).delete()

        hot_ranked = _fetch_hot_scores(hot_since)
        hot_filled = _fill_to_three(hot_ranked)
        inserted += _bulk_insert(HOT, hot_filled, base_date)

        share_ranked = _fetch_share_scores(share_since)
        share_filled = _fill_to_three(share_ranked)
        inserted += _bulk_insert(SHARE, share_filled, base_date)

    return inserted
