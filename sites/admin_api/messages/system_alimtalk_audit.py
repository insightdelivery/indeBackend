"""
시스템 경로(가입·문의 답변 등)에서 직접 호출한 카카오 알림톡을
`message_batch` / `message_detail` 에 남겨 `/admin/messages/sms/history` 에서 조회되게 한다.
"""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from .models import KakaoTemplate, MessageBatch, MessageDetail


def persist_system_kakao_alimtalk_precall_skip(
    *,
    phone_digits: str,
    recvname: str,
    syscode_sid: str,
    tpl_code: str,
    reason_code: str,
    reason_message: str,
    source: str,
    created_by_id: str = "",
) -> None:
    """
    알리고 API 호출 전에 중단된 경우(번호·시스코드·템플릿·발신번호·senderkey 등).
    발송 이력 화면에서 '요청은 했으나 전송 단계까지 못 감'을 확인할 수 있게 한다.
    """
    now = timezone.now()
    title = f"[알림톡 미발송] {reason_code}"[:200]
    body = (reason_message or "")[:8000]
    batch = MessageBatch.objects.create(
        type=MessageBatch.TYPE_KAKAO,
        sender="SYSTEM",
        title=title,
        content=body,
        total_count=1,
        success_count=0,
        fail_count=1,
        excluded_count=0,
        status=MessageBatch.STATUS_FAILED,
        is_processed=True,
        completed_at=now,
        request_snapshot={
            "source": source,
            "syscode_sid": syscode_sid,
            "tpl_code": tpl_code or None,
            "precall_skip": reason_code,
        },
        result_snapshot={
            "provider": "system_precall_skip",
            "reason": reason_code,
            "source": source,
        },
        api_response_logs=[],
        created_by_id=(created_by_id or "")[:15],
    )
    MessageDetail.objects.create(
        batch=batch,
        receiver_name=(recvname or "")[:80],
        receiver_phone=(phone_digits or "")[:30],
        final_content="",
        status=MessageDetail.STATUS_FAIL,
        error_reason=(reason_code or "precall_skip")[:200],
        external_message=(reason_message or "")[:500],
    )


def persist_system_kakao_alimtalk_batch(
    *,
    sender: str,
    tpl: KakaoTemplate | None,
    tpl_code: str,
    phone_digits: str,
    recvname: str,
    subject: str,
    final_message: str,
    aligo_result: dict[str, Any],
    source: str,
    created_by_id: str = "",
) -> None:
    """
    알리고 호출 직후 1건 배치로 기록한다. 성공/실패 모두 저장(알리고 콘솔과 무관하게 내부 이력용).
    """
    now = timezone.now()
    ok = bool(aligo_result.get("ok"))
    mid = str(aligo_result.get("mid") or "").strip() if ok else ""
    msg = str(aligo_result.get("message") or "")
    raw = aligo_result.get("raw")

    batch = MessageBatch.objects.create(
        type=MessageBatch.TYPE_KAKAO,
        sender=(sender or "")[:120],
        title=(subject or "")[:200],
        content=final_message or "",
        total_count=1,
        success_count=1 if ok else 0,
        fail_count=0 if ok else 1,
        excluded_count=0,
        status=MessageBatch.STATUS_COMPLETED if ok else MessageBatch.STATUS_FAILED,
        is_processed=True,
        completed_at=now,
        request_snapshot={
            "source": source,
            "tpl_code": tpl_code,
            "template_id": tpl.id if tpl else None,
        },
        result_snapshot={
            "provider": "aligo_kakao",
            "tpl_code": tpl_code,
            "mid": mid or None,
            "source": source,
        },
        api_response_logs=[raw] if raw is not None else [],
        created_by_id=(created_by_id or "")[:15],
    )
    MessageDetail.objects.create(
        batch=batch,
        receiver_name=(recvname or "")[:80],
        receiver_phone=(phone_digits or "")[:30],
        template_id=tpl.id if tpl else None,
        template_name=((tpl.template_name if tpl else "") or "")[:120],
        final_content=final_message or "",
        status=MessageDetail.STATUS_SUCCESS if ok else MessageDetail.STATUS_FAIL,
        external_code=(mid or "")[:50],
        external_message=(msg or "")[:500] if not ok else "",
        error_reason="" if ok else "provider_error",
        sent_at=now if ok else None,
    )
