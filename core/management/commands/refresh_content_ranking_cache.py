"""
하루 1회 실행 권장 (예: cron 00:10)
  python manage.py refresh_content_ranking_cache

특정 기준일(테스트용):
  python manage.py refresh_content_ranking_cache --base-date=2026-03-25
"""
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from sites.public_api.content_ranking_batch import run_content_ranking_refresh


class Command(BaseCommand):
    help = 'content_ranking_cache 갱신 (HOT/SHARE, schedulerContentPlan.md)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-date',
            type=str,
            default=None,
            help='집계 기준일 YYYY-MM-DD (기본: 오늘, TIME_ZONE 기준 localdate)',
        )

    def handle(self, *args, **options):
        raw = options.get('base_date')
        base_date = None
        if raw:
            base_date = datetime.strptime(raw.strip(), '%Y-%m-%d').date()

        n = run_content_ranking_refresh(base_date=base_date)
        d = base_date or timezone.localdate()
        self.stdout.write(self.style.SUCCESS(f'content_ranking_cache refreshed for {d}: {n} rows'))
