"""
카카오 알림톡 — 알리고(Aligo) akv10 API 전용 모듈.
문자 인증·SMS 대량(`aligo_sms.py`)과 분리한다. (_docsRules/1_planDoc/smsEmailSendPlan.md §4.4)

문서: https://smartsms.aligo.in/alimapi.html — POST /akv10/alimtalk/send/
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from django.conf import settings


ALIGO_KAKAO_ALIMTALK_SEND_URL = "https://kakaoapi.aligo.in/akv10/alimtalk/send/"


def send_alimtalk_with_aligo(
    sender: str,
    senderkey: str,
    tpl_code: str,
    items: list[dict[str, str]],
    reserve_at: datetime | None = None,
    failover: str = "N",
) -> dict[str, Any]:
    """
    알리고 알림톡 다건(최대 500) 동시 요청.

    items 각 원소: phone(필수), subject(필수), message(필수), recvname(선택)
    """
    apikey = (getattr(settings, "ALIGO_API_KEY", "") or "").strip()
    userid = (getattr(settings, "ALIGO_USER_ID", "") or "").strip()
    senderkey = (senderkey or "").strip()
    tpl_code = (tpl_code or "").strip()
    sender = "".join(ch for ch in (sender or "") if ch.isdigit())

    if not apikey or not userid:
        return {"ok": False, "message": "ALIGO_API_KEY 또는 ALIGO_USER_ID가 설정되지 않았습니다."}
    if not senderkey:
        return {"ok": False, "message": "ALIGO_KAKAO_SENDERKEY(발신프로필 키)가 설정되지 않았습니다."}
    if not tpl_code:
        return {"ok": False, "message": "알림톡 템플릿 코드(tpl_code)가 없습니다."}
    if not sender:
        return {"ok": False, "message": "발신번호(sender)가 올바르지 않습니다."}
    if not items:
        return {"ok": False, "message": "발송 대상이 없습니다."}
    if len(items) > 500:
        return {"ok": False, "message": "알리고 알림톡은 최대 500건까지 지원합니다."}

    test_mode = "Y" if bool(getattr(settings, "ALIGO_KAKAO_TEST_MODE", False)) else "N"

    payload: dict[str, str] = {
        "apikey": apikey,
        "userid": userid,
        "senderkey": senderkey,
        "tpl_code": tpl_code,
        "sender": sender,
        "failover": (failover or "N")[:1].upper() if (failover or "N")[:1].upper() in ("Y", "N") else "N",
        "testMode": test_mode,
    }
    if reserve_at is not None:
        payload["senddate"] = reserve_at.strftime("%Y%m%d%H%M%S")

    for idx, row in enumerate(items, start=1):
        phone = "".join(ch for ch in (row.get("phone") or "") if ch.isdigit())
        payload[f"receiver_{idx}"] = phone
        subj = (row.get("subject") or "").strip() or "알림"
        msg = row.get("message") or ""
        payload[f"subject_{idx}"] = subj[:200]
        payload[f"message_{idx}"] = msg
        recvname = (row.get("recvname") or "").strip()
        if recvname:
            payload[f"recvname_{idx}"] = recvname[:40]

    try:
        res = requests.post(ALIGO_KAKAO_ALIMTALK_SEND_URL, data=payload, timeout=60)
        res.raise_for_status()
        body = res.json()
    except requests.RequestException:
        return {"ok": False, "message": "알리고 알림톡 API 네트워크 오류"}
    except ValueError:
        return {"ok": False, "message": "알리고 알림톡 API 응답 파싱 실패"}

    code = body.get("code")
    try:
        code_int = int(code) if code is not None else -999
    except (TypeError, ValueError):
        code_int = -999

    if code_int != 0:
        return {"ok": False, "message": str(body.get("message") or "알리고 알림톡 발송 실패"), "raw": body}

    info = body.get("info") or {}
    if not isinstance(info, dict):
        info = {}
    scnt = int(info.get("scnt") or 0)
    mid = info.get("mid")

    return {
        "ok": True,
        "message": str(body.get("message") or ""),
        "success_cnt": scnt,
        "mid": mid,
        "raw": body,
    }
