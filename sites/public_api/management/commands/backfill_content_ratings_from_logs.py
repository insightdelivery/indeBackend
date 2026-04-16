"""
publicUserActivityLog RATING 집계 → Article.rating / Video.rating 백필.

  python manage.py backfill_content_ratings_from_logs
  python manage.py backfill_content_ratings_from_logs --dry-run
  python manage.py backfill_content_ratings_from_logs --content-type ARTICLE
  python manage.py backfill_content_ratings_from_logs --limit 100
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from sites.public_api.content_rating_sync import (
    ACTIVITY_RATING,
    CONTENT_TYPES_WITH_RATING_MASTER,
    sync_content_rating_aggregate,
)
from sites.public_api.models import PublicUserActivityLog


class Command(BaseCommand):
    help = (
        "publicUserActivityLog 의 RATING 을 집계해 Article.rating·Video.rating 에 반영합니다. "
        "POST /api/library/useractivity/rating 이전에 쌓인 로그만 있는 경우에 사용하세요."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="UPDATE 없이 처리 대상 (contentType, contentCode) 쌍 개수만 셉니다.",
        )
        parser.add_argument(
            "--content-type",
            type=str,
            default="",
            metavar="ARTICLE|VIDEO|SEMINAR",
            help="해당 타입만 처리합니다. 생략 시 ARTICLE·VIDEO·SEMINAR 전부.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="처리할 쌍의 최대 개수. 0이면 제한 없음.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        limit: int = max(0, int(options.get("limit") or 0))
        ct = (options.get("content_type") or "").strip().upper()

        if ct and ct not in CONTENT_TYPES_WITH_RATING_MASTER:
            self.stderr.write(self.style.ERROR(f"유효하지 않은 --content-type: {ct!r} (ARTICLE|VIDEO|SEMINAR)"))
            return

        base = PublicUserActivityLog.objects.filter(
            activity_type=ACTIVITY_RATING,
            rating_value__isnull=False,
            content_type__in=CONTENT_TYPES_WITH_RATING_MASTER,
        )
        if ct:
            base = base.filter(content_type=ct)

        distinct_qs = (
            base.values("content_type", "content_code")
            .distinct()
            .order_by("content_type", "content_code")
        )

        processed = 0
        for row in distinct_qs.iterator(chunk_size=500):
            if limit and processed >= limit:
                break
            c_type = row["content_type"]
            code = row["content_code"]
            processed += 1
            if dry_run:
                continue
            with transaction.atomic():
                sync_content_rating_aggregate(c_type, code)
            if processed % 500 == 0:
                self.stdout.write(f"... synced {processed} pairs")

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[dry-run] RATING 이 있는 고유 (contentType, contentCode) 쌍: {processed}개"))
        else:
            self.stdout.write(self.style.SUCCESS(f"완료: {processed}개 쌍 동기화"))
