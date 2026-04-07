"""
일 1회 콘텐츠 랭킹 캐시 갱신 (schedulerContentPlan.md)
- publicUserActivityLog 집계 → content_ranking_cache, 트랜잭션 단위 삭제 후 재삽입
- CATEGORY_HOT: JOIN article, VIEW는 COUNT만, ROW_NUMBER로 카테고리별 TOP 30 → 부족 시 최신 발행으로 채움
- RECOMMENDED: 발행 아티클 최신순 후보 풀(목표 50)에서 배치 1회 랜덤 3건 (§D)
- WEEKLY_CROSS: ARTICLE/VIDEO/SEMINAR 통합, 최근 7일 VIEW 합 상위 3건 (§E)
"""
from __future__ import annotations

import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import DefaultDict, List, Tuple

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from sites.public_api.models import ContentRankingCache

ARTICLE = 'ARTICLE'
VIDEO = 'VIDEO'
SEMINAR = 'SEMINAR'
HOT = ContentRankingCache.RANKING_HOT
SHARE = ContentRankingCache.RANKING_SHARE
CATEGORY_HOT = ContentRankingCache.RANKING_CATEGORY_HOT
RECOMMENDED = ContentRankingCache.RANKING_RECOMMENDED
WEEKLY_CROSS = ContentRankingCache.RANKING_WEEKLY_CROSS

RECOMMENDED_POOL_SIZE = 50
RECOMMENDED_PICK = 3


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


def _recommended_candidate_pool() -> List[str]:
    """
    §D.4·D.4.1: 발행 아티클 전체를 createdAt DESC로 두고 상위 목표 50개를 후보 풀로 한다.
    발행 건수가 50 미만이면 가용한 만큼만 반환한다.
    """
    all_codes = _published_article_codes_recent_first()
    return all_codes[:RECOMMENDED_POOL_SIZE]


def _pick_recommended_random(candidates: List[str]) -> List[Tuple[str, float]]:
    """후보 풀에서 랜덤 RECOMMENDED_PICK건. 풀이 그보다 작으면 가능한 만큼만."""
    if not candidates:
        return []
    k = min(RECOMMENDED_PICK, len(candidates))
    picked = random.sample(candidates, k=k)
    return [(code, 0.0) for code in picked]


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


def _fetch_weekly_cross_view_scores(since: datetime) -> List[Tuple[str, str, float]]:
    """
    아티클·비디오·세미나 구분 없이 최근 구간 VIEW의 viewCount 합 상위 3.
    Returns: (content_type, content_code, score)
    """
    sql = """
        SELECT contentType, contentCode, COALESCE(SUM(viewCount), 0) AS score
        FROM publicUserActivityLog
        WHERE activityType = 'VIEW'
          AND contentType IN ('ARTICLE', 'VIDEO', 'SEMINAR')
          AND regDateTime >= %s
        GROUP BY contentType, contentCode
        ORDER BY score DESC, contentType ASC, contentCode DESC
        LIMIT 3
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [since])
        out: List[Tuple[str, str, float]] = []
        for row in cursor.fetchall():
            out.append((str(row[0]), str(row[1]).strip(), _to_float(row[2])))
        return out


def _fill_weekly_cross_to_three(ranked: List[Tuple[str, str, float]]) -> List[Tuple[str, str, float]]:
    """집계 상위 + 발행 아티클 최신순으로 3건(ARTICLE만 보충, 결정적)."""
    need = 3
    seen = {(ct, cc) for ct, cc, _ in ranked}
    out: List[Tuple[str, str, float]] = list(ranked[:need])
    for code in _published_article_codes_recent_first():
        if len(out) >= need:
            break
        if (ARTICLE, code) in seen:
            continue
        seen.add((ARTICLE, code))
        out.append((ARTICLE, code, 0.0))
    return out[:need]


def _bulk_insert_weekly_cross(rows: List[Tuple[str, str, float]], base_date: date) -> int:
    if not rows:
        return 0
    objs = [
        ContentRankingCache(
            ranking_type=WEEKLY_CROSS,
            content_type=ct,
            content_code=code,
            score=score,
            rank_order=i,
            base_date=base_date,
            category_code=None,
        )
        for i, (ct, code, score) in enumerate(rows, start=1)
    ]
    ContentRankingCache.objects.bulk_create(objs)
    return len(objs)


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


def _fetch_share_scores_for_type(content_type: str, since: datetime) -> List[Tuple[str, float]]:
    """비디오·세미나 공유 집계(아티클 SHARE와 동일 규칙)."""
    sql = """
        SELECT contentCode, COALESCE(SUM(viewCount), 0) AS score
        FROM publicUserActivityLog
        WHERE contentType = %s
          AND activityType = 'SHARE'
          AND regDateTime >= %s
        GROUP BY contentCode
        ORDER BY score DESC, contentCode DESC
        LIMIT 3
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [content_type, since])
        return [(row[0], _to_float(row[1])) for row in cursor.fetchall()]


def _published_video_codes_recent_first(api_ct: str) -> List[str]:
    """api_ct: VIDEO | SEMINAR — 공개 Video PK 문자열 최신순."""
    from sites.admin_api.video.models import Video

    lc = 'video' if api_ct == VIDEO else 'seminar'
    qs = (
        Video.objects.filter(deletedAt__isnull=True, status='public', contentType=lc)
        .order_by('-createdAt')
        .values_list('id', flat=True)
    )
    return [str(pk) for pk in qs]


def _fill_to_three_codes(
    ranked: List[Tuple[str, float]],
    fallback_codes: List[str],
) -> List[Tuple[str, float]]:
    """아티클 _fill_to_three와 동일: 상위 후보 + fallback으로 3건."""
    need = 3
    seen = {str(code).strip() for code, _ in ranked}
    out: List[Tuple[str, float]] = list(ranked[:need])
    for code in fallback_codes:
        if len(out) >= need:
            break
        c = str(code).strip()
        if not c or c in seen:
            continue
        seen.add(c)
        out.append((c, 0.0))
    return out[:need]


def _fetch_category_hot_ranked_rows(since: datetime) -> List[Tuple[str, str, float, int]]:
    """
    카테고리별 score 상위 30 (ROW_NUMBER). MySQL 8+.
    Returns: (category_code, content_code, score, rn)
    """
    sql = """
        SELECT category_code, content_code, score, rn
        FROM (
            SELECT
                category_code,
                content_code,
                score,
                ROW_NUMBER() OVER (
                    PARTITION BY category_code
                    ORDER BY score DESC, content_code DESC
                ) AS rn
            FROM (
                SELECT
                    a.category AS category_code,
                    l.contentCode AS content_code,
                    (
                        COALESCE(AVG(CASE WHEN l.activityType = 'RATING' THEN l.ratingValue END), 0) * 5
                        + COUNT(CASE WHEN l.activityType = 'BOOKMARK' THEN 1 END) * 3
                        + COUNT(CASE WHEN l.activityType = 'VIEW' THEN 1 END)
                    ) AS score
                FROM publicUserActivityLog l
                INNER JOIN article a
                    ON CAST(a.id AS CHAR) = l.contentCode
                    AND a.deletedAt IS NULL
                    AND a.status = 'SYS26209B021'
                WHERE l.contentType = 'ARTICLE'
                  AND l.regDateTime >= %s
                GROUP BY a.category, l.contentCode
            ) per_article
        ) ranked
        WHERE rn <= 30
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [since])
        out: List[Tuple[str, str, float, int]] = []
        for row in cursor.fetchall():
            out.append((str(row[0]), str(row[1]), _to_float(row[2]), int(row[3])))
        return out


def _published_category_article_ids_recent_first(category: str) -> List[str]:
    """공개 목록과 동일: SYS26209B021만."""
    from sites.admin_api.articles.models import Article

    return [
        str(pk)
        for pk in Article.objects.filter(deletedAt__isnull=True, category=category)
        .filter(Q(status='SYS26209B021'))
        .order_by('-createdAt')
        .values_list('id', flat=True)
    ]


def _all_published_category_codes() -> List[str]:
    from sites.admin_api.articles.models import Article

    qs = (
        Article.objects.filter(deletedAt__isnull=True)
        .filter(Q(status='SYS26209B021'))
        .values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )
    return list(qs)


def _fill_category_hot_to_thirty(
    category: str,
    ranked_rows: List[Tuple[str, float, int]],
) -> List[Tuple[str, float, int]]:
    """
    ranked_rows: (content_code, score, rn) 정렬됨
    반환: (content_code, score, rank_order) 길이 ≤30, rank_order 1..
    """
    ranked_rows = sorted(ranked_rows, key=lambda x: x[2])
    seen: set[str] = set()
    out: List[Tuple[str, float, int]] = []
    for code, score, _rn in ranked_rows:
        c = str(code).strip()
        if not c or c in seen:
            continue
        seen.add(c)
        out.append((c, score, len(out) + 1))
    for code in _published_category_article_ids_recent_first(category):
        if len(out) >= 30:
            break
        if code in seen:
            continue
        seen.add(code)
        out.append((code, 0.0, len(out) + 1))
    return out


def _build_category_hot_insert_rows(since: datetime) -> List[Tuple[str, str, float, int]]:
    grouped: DefaultDict[str, List[Tuple[str, float, int]]] = defaultdict(list)
    try:
        for cat, code, score, rn in _fetch_category_hot_ranked_rows(since):
            grouped[cat].append((code, score, rn))
    except Exception:
        grouped.clear()

    flat: List[Tuple[str, str, float, int]] = []
    for cat in _all_published_category_codes():
        filled = _fill_category_hot_to_thirty(cat, grouped.get(cat, []))
        for code, score, ro in filled:
            flat.append((cat, code, score, ro))
    return flat


def _bulk_insert(
    ranking_type: str,
    rows: List[Tuple[str, float]],
    base_date: date,
    content_type: str = ARTICLE,
) -> int:
    objs = [
        ContentRankingCache(
            ranking_type=ranking_type,
            content_type=content_type,
            content_code=code,
            score=score,
            rank_order=i,
            base_date=base_date,
            category_code=None,
        )
        for i, (code, score) in enumerate(rows, start=1)
    ]
    ContentRankingCache.objects.bulk_create(objs)
    return len(objs)


def _bulk_insert_category_hot(rows: List[Tuple[str, str, float, int]], base_date: date) -> int:
    objs = [
        ContentRankingCache(
            ranking_type=CATEGORY_HOT,
            content_type=ARTICLE,
            category_code=cat,
            content_code=code,
            score=score,
            rank_order=ro,
            base_date=base_date,
        )
        for cat, code, score, ro in rows
    ]
    if not objs:
        return 0
    ContentRankingCache.objects.bulk_create(objs)
    return len(objs)


def run_content_ranking_refresh(base_date: date | None = None) -> int:
    """
    당일 base_date 캐시를 비우고 HOT·SHARE 각 3건, CATEGORY_HOT, RECOMMENDED 3건, WEEKLY_CROSS 3건을 다시 적재한다.
    Returns: 삽입된 총 행 수.
    """
    if base_date is None:
        base_date = timezone.localdate()

    now = timezone.now()
    hot_since = now - timedelta(days=14)
    share_since = now - timedelta(days=30)
    weekly_since = now - timedelta(days=7)

    inserted = 0
    with transaction.atomic():
        ContentRankingCache.objects.filter(base_date=base_date).delete()

        hot_ranked = _fetch_hot_scores(hot_since)
        hot_filled = _fill_to_three(hot_ranked)
        inserted += _bulk_insert(HOT, hot_filled, base_date)

        share_ranked = _fetch_share_scores(share_since)
        share_filled = _fill_to_three(share_ranked)
        inserted += _bulk_insert(SHARE, share_filled, base_date)

        share_video_ranked = _fetch_share_scores_for_type(VIDEO, share_since)
        share_video_filled = _fill_to_three_codes(
            share_video_ranked, _published_video_codes_recent_first(VIDEO)
        )
        inserted += _bulk_insert(SHARE, share_video_filled, base_date, VIDEO)

        share_seminar_ranked = _fetch_share_scores_for_type(SEMINAR, share_since)
        share_seminar_filled = _fill_to_three_codes(
            share_seminar_ranked, _published_video_codes_recent_first(SEMINAR)
        )
        inserted += _bulk_insert(SHARE, share_seminar_filled, base_date, SEMINAR)

        cat_rows = _build_category_hot_insert_rows(hot_since)
        inserted += _bulk_insert_category_hot(cat_rows, base_date)

        rec_pool = _recommended_candidate_pool()
        rec_rows = _pick_recommended_random(rec_pool)
        inserted += _bulk_insert(RECOMMENDED, rec_rows, base_date)

        try:
            weekly_ranked = _fetch_weekly_cross_view_scores(weekly_since)
        except Exception:
            weekly_ranked = []
        weekly_filled = _fill_weekly_cross_to_three(weekly_ranked)
        inserted += _bulk_insert_weekly_cross(weekly_filled, base_date)

    return inserted
