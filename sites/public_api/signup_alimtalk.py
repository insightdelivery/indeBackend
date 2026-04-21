"""
회원 이름 치환 카카오 알림톡 (알리고 akv10) — sysCodeManager.sysCodeVal = tpl_code.

- 사용처: 회원가입 완료(`SYS26421B003`), 1:1 문의 답변 안내(`SYS26421B004`) 등.
- 시스템 코드: **`sysCodeManager`** (`core.SysCodeManager`) 행의 `sysCodeSid`·`sysCodeVal`(tpl_code)·`sysCodeUse='Y'`.
- `kakao_templates` 승인 건 `content` 본문에서 등록 **이름**으로 치환: `{이름}`·`#{이름}#`·`{회원}`·`#{회원}#` (비어 있으면 `"회원"`).
- 발신번호: 승인된 `message_sender_number` 최신 1건 (`/admin/messages/sms/send` 와 동일 출처).
- 알리고 호출 후 **`message_batch` / `message_detail`** 에 1건 기록 → `/admin/messages/sms/history` 에서 확인 가능.
- 실패 시에도 예외는 없고, 배치는 `failed` 로 남긴다.
"""
from __future__ import annotations

import logging
import re

from django.conf import settings

from core.models import SysCodeManager
from sites.admin_api.messages.aligo_kakao import send_alimtalk_with_aligo
from sites.admin_api.messages.models import KakaoTemplate, MessageSenderNumber
from sites.admin_api.messages.system_alimtalk_audit import (
    persist_system_kakao_alimtalk_batch,
    persist_system_kakao_alimtalk_precall_skip,
)
from sites.public_api.phone_normalize import is_valid_kr_mobile, normalize_phone_kr

logger = logging.getLogger(__name__)

# 코드관리(sysCodeManager.sysCodeSid) — sysCodeVal 에 알리고 템플릿 코드
SYSCODE_SIGNUP_KAKAO_TEMPLATE = "SYS26421B003"
SYSCODE_INQUIRY_ANSWER_KAKAO_TEMPLATE = "SYS26421B004"


def _apply_member_placeholder(template_body: str, member_name: str) -> str:
    """관리자 문자/카카오 발송 화면과 동일하게 `{이름}`·`{회원}` 계열을 가입 시 저장된 이름으로 치환."""
    name = (member_name or "").strip() or "회원"
    text = template_body or ""
    for key in ("이름", "회원"):
        text = text.replace(f"{{{key}}}", name).replace(f"#{{{key}}}#", name)
    return text


def try_send_syscode_member_alimtalk(
    *,
    syscode_sid: str,
    phone: str,
    member_name: str,
    created_by_id: str = "",
    audit_source: str = "syscode_kakao",
) -> None:
    """
    :param syscode_sid: sysCodeManager.sysCodeSid (예: SYS26421B004).
    :param phone: 수신 번호(가능하면 정규화된 값).
    :param member_name: `{이름}`·`{회원}` 등 치환용(가입·문의 시 저장된 이름).
    :param created_by_id: 관리자 발송 시 `memberShipSid` (선택).
    :param audit_source: 이력 `request_snapshot.source` 구분값.
    """
    recv = (member_name or "").strip()[:80]

    def _precall_skip(reason_code: str, reason_message: str, phone_d: str = "", tpl_c: str = "") -> None:
        try:
            persist_system_kakao_alimtalk_precall_skip(
                phone_digits=phone_d,
                recvname=recv,
                syscode_sid=syscode_sid,
                tpl_code=tpl_c,
                reason_code=reason_code,
                reason_message=reason_message,
                source=audit_source,
                created_by_id=created_by_id,
            )
        except Exception as exc:
            logger.exception("syscode_alimtalk: precall_skip persist failed sid=%s err=%s", syscode_sid, exc)

    phone_norm = normalize_phone_kr(phone or "")
    phone_digits = "".join(ch for ch in phone_norm if ch.isdigit())
    if not is_valid_kr_mobile(phone_norm) or not re.match(r"^01\d{8,9}$", phone_digits):
        logger.warning("syscode_alimtalk: skip invalid phone (sid=%s)", syscode_sid)
        _precall_skip(
            "invalid_phone",
            "휴대폰 번호가 올바르지 않아 알리고 호출을 하지 않았습니다.",
            phone_d=phone_digits,
        )
        return

    sc = (
        SysCodeManager.objects.filter(
            sysCodeSid=syscode_sid,
            sysCodeUse="Y",
        )
        .only("sysCodeVal")
        .first()
    )
    if not sc:
        logger.warning("syscode_alimtalk: sysCodeManager row missing or not Y (sid=%s)", syscode_sid)
        _precall_skip(
            "syscode_missing",
            f"sysCodeManager 에 sysCodeSid={syscode_sid}, sysCodeUse=Y 인 행이 없습니다.",
            phone_d=phone_digits,
        )
        return
    tpl_code = (sc.sysCodeVal or "").strip()
    if not tpl_code:
        logger.warning("syscode_alimtalk: sysCodeVal empty (sid=%s)", syscode_sid)
        _precall_skip(
            "syscode_val_empty",
            f"sysCodeManager.sysCodeVal 이 비어 있습니다 (sid={syscode_sid}).",
            phone_d=phone_digits,
        )
        return

    tpl = (
        KakaoTemplate.objects.filter(
            template_code=tpl_code,
            status=KakaoTemplate.STATUS_APPROVED,
        )
        .order_by("-id")
        .first()
    )
    if not tpl:
        logger.warning(
            "syscode_alimtalk: no approved KakaoTemplate for template_code=%s (sid=%s)",
            tpl_code,
            syscode_sid,
        )
        _precall_skip(
            "kakao_template_missing",
            f"kakao_templates 에 template_code={tpl_code} 승인(approved) 템플릿이 없습니다.",
            phone_d=phone_digits,
            tpl_c=tpl_code,
        )
        return

    sender = (
        MessageSenderNumber.objects.filter(
            status=MessageSenderNumber.STATUS_APPROVED,
            deleted_at__isnull=True,
        )
        .order_by("-id")
        .values_list("sender_number", flat=True)
        .first()
    )
    if not sender:
        logger.warning("syscode_alimtalk: no approved message_sender_number (sid=%s)", syscode_sid)
        _precall_skip(
            "sender_number_missing",
            "승인된 발신번호(message_sender_number)가 없습니다.",
            phone_d=phone_digits,
            tpl_c=tpl_code,
        )
        return

    senderkey = (getattr(settings, "ALIGO_KAKAO_SENDERKEY", "") or "").strip()
    if not senderkey:
        logger.warning("syscode_alimtalk: ALIGO_KAKAO_SENDERKEY not set (sid=%s)", syscode_sid)
        _precall_skip(
            "aligo_senderkey_missing",
            "환경변수 ALIGO_KAKAO_SENDERKEY 가 설정되지 않았습니다.",
            phone_d=phone_digits,
            tpl_c=tpl_code,
        )
        return

    from sites.admin_api.messages.views import _kakao_alimtalk_extras_from_template

    message_body = _apply_member_placeholder(tpl.content, member_name)
    subject = ((tpl.template_name or "").strip() or "알림")[:200]
    recvname = (member_name or "").strip()[:40]
    emt, btn = _kakao_alimtalk_extras_from_template(tpl)

    out = send_alimtalk_with_aligo(
        sender,
        senderkey,
        tpl_code,
        [
            {
                "phone": phone_digits,
                "subject": subject,
                "message": message_body,
                "recvname": recvname,
            }
        ],
        reserve_at=None,
        batch_emtitle=emt,
        batch_button=btn,
    )
    if not out.get("ok"):
        logger.warning(
            "syscode_alimtalk: aligo failed sid=%s msg=%s",
            syscode_sid,
            out.get("message"),
        )

    try:
        persist_system_kakao_alimtalk_batch(
            sender=sender,
            tpl=tpl,
            tpl_code=tpl_code,
            phone_digits=phone_digits,
            recvname=recvname,
            subject=subject,
            final_message=message_body,
            aligo_result=out,
            source=audit_source,
            created_by_id=created_by_id,
        )
    except Exception as exc:
        logger.exception("syscode_alimtalk: persist batch failed sid=%s err=%s", syscode_sid, exc)


def try_send_signup_complete_alimtalk(*, phone: str, member_name: str) -> None:
    """회원가입 완료 — `SYS26421B003`."""
    try_send_syscode_member_alimtalk(
        syscode_sid=SYSCODE_SIGNUP_KAKAO_TEMPLATE,
        phone=phone,
        member_name=member_name,
        audit_source="signup_kakao_alimtalk",
    )
