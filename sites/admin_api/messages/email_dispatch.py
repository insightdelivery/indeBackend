"""
관리자 이메일 배치 발송 — core.mail.send_email(Gmail SMTP) 사용.
"""
from __future__ import annotations

import html
from typing import Any

from django.utils import timezone

from core.mail import send_email

from .models import MessageBatch, MessageDetail

def _plain_body_to_html(text: str) -> str:
    return (
        '<div style="white-space:pre-wrap;font-family:sans-serif;font-size:14px;line-height:1.5">'
        f"{html.escape(text)}"
        "</div>"
    )


def send_email_batch_details(batch: MessageBatch, *, now=None) -> dict[str, Any]:
    """
    배치에 속한 수신 성공(status=success) 상세 건만 SMTP로 발송하고 상세 행을 갱신한다.
    즉시 발송·예약 발송 처리 공통으로 사용한다.

    Returns:
        success_count, fail_count, logs (api_response_logs용 요약)
    """
    now = now or timezone.now()
    snap = batch.request_snapshot if isinstance(batch.request_snapshot, dict) else {}
    display_name = (snap.get("senderDisplayName") or "").strip() or None
    from_addr = (batch.sender or "").strip()
    subject = (batch.title or "").strip() or "(제목 없음)"

    details = list(
        MessageDetail.objects.filter(batch=batch, status=MessageDetail.STATUS_SUCCESS).order_by("id")
    )
    success_n = 0
    fail_n = 0
    logs: list[dict[str, Any]] = []

    for d in details:
        body = (d.final_content or batch.content or "").strip()
        if not body:
            body = " "
        to = (d.receiver_email or "").strip()
        if not to:
            d.status = MessageDetail.STATUS_FAIL
            d.error_reason = "missing_receiver_email"
            d.external_message = "수신 이메일 없음"
            d.save(update_fields=["status", "error_reason", "external_message", "updated_at"])
            fail_n += 1
            logs.append({"to": "", "ok": False, "reason": "missing_receiver_email"})
            continue

        ok = send_email(
            to,
            subject,
            _plain_body_to_html(body),
            body_text=body,
            from_email=from_addr or None,
            from_display_name=display_name,
            reply_to=from_addr or None,
        )
        if ok:
            d.status = MessageDetail.STATUS_SUCCESS
            d.sent_at = now
            d.error_reason = ""
            d.external_message = "smtp_ok"
            success_n += 1
        else:
            d.status = MessageDetail.STATUS_FAIL
            d.error_reason = "smtp_send_failed"
            d.external_message = "Gmail SMTP 발송 실패 또는 GMAIL_SENDER/앱비밀번호 미설정"
            fail_n += 1
        d.save(
            update_fields=[
                "status",
                "sent_at",
                "error_reason",
                "external_message",
                "updated_at",
            ]
        )
        logs.append({"to": to, "ok": ok})

    return {
        "success": success_n,
        "fail": fail_n,
        "logs": logs,
    }
