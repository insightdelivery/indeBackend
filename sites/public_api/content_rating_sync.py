"""
콘텐츠 마스터(Article / Video·세미나) rating 필드와 publicUserActivityLog RATING 집계 동기화.
- POST /api/library/useractivity/rating 및 백필 커맨드에서 공통 사용.
"""
from django.db.models import Avg, Count

from sites.admin_api.articles.models import Article
from sites.admin_api.video.models import Video
from sites.public_api.models import PublicUserActivityLog

CONTENT_TYPES_WITH_RATING_MASTER = frozenset({'ARTICLE', 'VIDEO', 'SEMINAR'})
ACTIVITY_RATING = 'RATING'


def sync_content_rating_aggregate(content_type: str, content_code: str) -> None:
    """
    publicUserActivityLog 의 RATING 평균을 관리자 마스터(Article.rating / Video.rating)에 반영.
    별점 로그가 없으면 rating=NULL.
    """
    cc = str(content_code or '').strip()
    if not cc or content_type not in CONTENT_TYPES_WITH_RATING_MASTER:
        return
    try:
        pk = int(cc, 10)
    except (TypeError, ValueError):
        return
    if pk < 1:
        return

    agg = PublicUserActivityLog.objects.filter(
        content_type=content_type,
        content_code=cc,
        activity_type=ACTIVITY_RATING,
        rating_value__isnull=False,
    ).aggregate(avg=Avg('rating_value'), cnt=Count('public_user_activity_log_id'))
    cnt = agg['cnt'] or 0
    avg = agg['avg']
    new_rating = round(float(avg), 2) if cnt > 0 and avg is not None else None

    if content_type == 'ARTICLE':
        Article.objects.filter(id=pk, deletedAt__isnull=True).update(rating=new_rating)
    elif content_type == 'VIDEO':
        Video.objects.filter(id=pk, contentType__iexact='video', deletedAt__isnull=True).update(rating=new_rating)
    elif content_type == 'SEMINAR':
        Video.objects.filter(id=pk, contentType__iexact='seminar', deletedAt__isnull=True).update(rating=new_rating)
