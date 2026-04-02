"""
예약된 관리자 이메일 배치(type=email, status=scheduled, scheduled_at 도래)를 SMTP로 발송한다.
cron 등에서 1~5분 간격으로 실행 권장.

  python manage.py send_scheduled_admin_emails
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from sites.admin_api.messages.email_dispatch import send_email_batch_details
from sites.admin_api.messages.models import MessageBatch


class Command(BaseCommand):
    help = "예약 시각이 지난 이메일 메시지 배치를 Gmail SMTP로 발송합니다."

    def handle(self, *args, **options):
        now = timezone.now()
        qs = (
            MessageBatch.objects.filter(
                type=MessageBatch.TYPE_EMAIL,
                status=MessageBatch.STATUS_SCHEDULED,
                is_processed=False,
                scheduled_at__isnull=False,
                scheduled_at__lte=now,
            )
            .order_by("scheduled_at", "id")
        )
        n = qs.count()
        if n == 0:
            self.stdout.write(self.style.SUCCESS("처리할 예약 이메일 배치가 없습니다."))
            return

        self.stdout.write(f"예약 이메일 배치 {n}건 처리 시작…")
        for batch in qs:
            try:
                with transaction.atomic():
                    locked = MessageBatch.objects.select_for_update().get(pk=batch.pk)
                    if locked.status != MessageBatch.STATUS_SCHEDULED or locked.is_processed:
                        continue
                    out = send_email_batch_details(locked, now=timezone.now())
                    locked.success_count = out["success"]
                    locked.fail_count = out["fail"]
                    locked.api_response_logs = out.get("logs") or []
                    locked.result_snapshot = {
                        "provider": "gmail_smtp",
                        "scheduled": True,
                    }
                    locked.is_processed = True
                    locked.completed_at = timezone.now()
                    locked.status = (
                        MessageBatch.STATUS_COMPLETED
                        if out["fail"] == 0
                        else MessageBatch.STATUS_FAILED
                    )
                    locked.save(
                        update_fields=[
                            "success_count",
                            "fail_count",
                            "api_response_logs",
                            "result_snapshot",
                            "is_processed",
                            "completed_at",
                            "status",
                            "updated_at",
                        ]
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  배치 id={batch.id} 완료: 성공 {out['success']}, 실패 {out['fail']}"
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  배치 id={batch.id} 오류: {e}"))

        self.stdout.write(self.style.SUCCESS("처리 종료."))
