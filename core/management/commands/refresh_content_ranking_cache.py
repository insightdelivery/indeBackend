"""
하루 1회 실행 권장 (예: cron 00:10)
  python manage.py migrate public_api   # 최초 1회 — content_ranking_cache.category_code (0015)
  python manage.py refresh_content_ranking_cache
  # 적재: HOT·SHARE·CATEGORY_HOT·RECOMMENDED(§D)·WEEKLY_CROSS(§E)

특정 기준일(테스트용):
  python manage.py refresh_content_ranking_cache --base-date=2026-03-25
"""
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import OperationalError
from django.utils import timezone

from sites.public_api.content_ranking_batch import run_content_ranking_refresh


class Command(BaseCommand):
    help = 'content_ranking_cache 갱신 (HOT/SHARE/CATEGORY_HOT/RECOMMENDED/WEEKLY_CROSS, schedulerContentPlan.md)'

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

        try:
            n = run_content_ranking_refresh(base_date=base_date)
        except OperationalError as e:
            err = str(e).lower()
            if 'category_code' in err and 'unknown column' in err:
                self.stderr.write(
                    self.style.ERROR(
                        'content_ranking_cache 테이블에 category_code 컬럼이 없습니다.\n'
                        '다음을 실행한 뒤 다시 시도하세요:\n'
                        '  python manage.py migrate public_api'
                    )
                )
                raise SystemExit(1) from e
            raise
        d = base_date or timezone.localdate()
        self.stdout.write(self.style.SUCCESS(f'content_ranking_cache refreshed for {d}: {n} rows'))
