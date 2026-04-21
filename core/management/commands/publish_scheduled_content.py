"""
예약 발행 시각이 지난 아티클·비디오·세미나를 공개(즉시발행/공개 SID)로 전환한다.
cron 등에서 1분 간격 실행을 전제로 한다.

  python manage.py publish_scheduled_content
  python manage.py publish_scheduled_content --dry-run
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from sites.admin_api.articles.models import Article
from sites.admin_api.content_publish_syscodes import STATUS_PUBLISHED, STATUS_SCHEDULED
from sites.admin_api.video.models import Video


def _due_filter(now):
    return dict(
        deletedAt__isnull=True,
        status=STATUS_SCHEDULED,
        scheduledAt__isnull=False,
        scheduledAt__lte=now,
    )


class Command(BaseCommand):
    help = (
        "예약 발행(SYS26209B024)이며 scheduledAt이 현재 이전인 미삭제 콘텐츠를 "
        "즉시발행·공개(SYS26209B021)로 바꿉니다. (아티클 + 비디오/세미나 video 테이블)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="DB를 갱신하지 않고 대상 id만 출력합니다.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        now = timezone.now()
        flt = _due_filter(now)

        article_qs = Article.objects.filter(**flt).order_by("scheduledAt", "id")
        video_qs = Video.objects.filter(**flt).order_by("scheduledAt", "id")

        article_ids = list(article_qs.values_list("id", flat=True))
        video_rows = list(video_qs.values_list("id", "contentType"))

        if not article_ids and not video_rows:
            self.stdout.write(self.style.SUCCESS("처리할 예약 발행 도래 건이 없습니다."))
            return

        self.stdout.write(
            f"예약 도래: 아티클 {len(article_ids)}건, 비디오·세미나 {len(video_rows)}건"
            + (" (dry-run)" if dry_run else "")
        )
        if article_ids:
            self.stdout.write(f"  article ids: {article_ids}")
        if video_rows:
            self.stdout.write(f"  video rows (id, contentType): {video_rows}")

        if dry_run:
            self.stdout.write(self.style.WARNING("dry-run 이므로 저장하지 않았습니다."))
            return

        video_ids = [r[0] for r in video_rows]
        with transaction.atomic():
            n_art = Article.objects.filter(pk__in=article_ids).update(
                status=STATUS_PUBLISHED,
                updatedAt=now,
            )
            n_vid = Video.objects.filter(pk__in=video_ids).update(
                status=STATUS_PUBLISHED,
                updatedAt=now,
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"완료: article {n_art}행, video {n_vid}행을 공개(SYS26209B021)로 갱신했습니다."
            )
        )
