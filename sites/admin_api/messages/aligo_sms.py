from __future__ import annotations

from datetime import datetime
from typing import Iterable

import requests
from django.conf import settings


ALIGO_SEND_MASS_URL = "https://apis.aligo.in/send_mass/"
ALIGO_SMS_LIST_URL = "https://apis.aligo.in/sms_list/"


def _euc_kr_len(text: str) -> int:
    try:
        return len((text or "").encode("euc-kr"))
    except UnicodeEncodeError:
        # EUC-KR 인코딩 불가 문자는 치환 기준으로 계산
        return len((text or "").encode("euc-kr", errors="replace"))


def infer_msg_type(contents: Iterable[str]) -> str:
    # 알리고 권장 규칙: 90 byte 초과 시 LMS
    return "LMS" if any(_euc_kr_len(c) > 90 for c in contents) else "SMS"


def send_mass_with_aligo(
    sender: str,
    title: str,
    phones: list[str],
    messages: list[str],
    reserve_at: datetime | None = None,
) -> dict:
    api_key = (getattr(settings, "ALIGO_API_KEY", "") or "").strip()
    user_id = (getattr(settings, "ALIGO_USER_ID", "") or "").strip()
    if not api_key or not user_id:
        return {"ok": False, "message": "ALIGO_API_KEY 또는 ALIGO_USER_ID가 설정되지 않았습니다."}
    if not phones or not messages or len(phones) != len(messages):
        return {"ok": False, "message": "발송 대상 데이터가 올바르지 않습니다."}
    if len(phones) > 500:
        return {"ok": False, "message": "알리고 send_mass는 최대 500건까지 지원합니다."}

    payload = {
        "key": api_key,
        "user_id": user_id,
        "sender": sender,
        "cnt": str(len(phones)),
        "msg_type": infer_msg_type(messages),
    }
    if title:
        payload["title"] = title
    if reserve_at is not None:
        payload["rdate"] = reserve_at.strftime("%Y%m%d")
        payload["rtime"] = reserve_at.strftime("%H%M")

    for idx, (phone, msg) in enumerate(zip(phones, messages), start=1):
        payload[f"rec_{idx}"] = phone
        payload[f"msg_{idx}"] = msg

    try:
        res = requests.post(ALIGO_SEND_MASS_URL, data=payload, timeout=20)
        res.raise_for_status()
        body = res.json()
    except requests.RequestException:
        return {"ok": False, "message": "알리고 API 네트워크 오류"}
    except ValueError:
        return {"ok": False, "message": "알리고 API 응답 파싱 실패"}

    code = str(body.get("result_code", ""))
    if code != "1":
        return {"ok": False, "message": body.get("message") or "알리고 발송 실패", "raw": body}

    return {
        "ok": True,
        "message": body.get("message", ""),
        "msg_id": body.get("msg_id"),
        "success_cnt": int(body.get("success_cnt") or 0),
        "error_cnt": int(body.get("error_cnt") or 0),
        "msg_type": body.get("msg_type"),
        "raw": body,
    }


def fetch_sms_list_all(mid: str | int, page_size: int = 500) -> dict:
    api_key = (getattr(settings, "ALIGO_API_KEY", "") or "").strip()
    user_id = (getattr(settings, "ALIGO_USER_ID", "") or "").strip()
    if not api_key or not user_id:
        return {"ok": False, "message": "ALIGO_API_KEY 또는 ALIGO_USER_ID가 설정되지 않았습니다."}

    page = 1
    merged: list[dict] = []
    raws: list[dict] = []
    while True:
        payload = {
            "key": api_key,
            "user_id": user_id,
            "mid": str(mid),
            "page": str(page),
            "page_size": str(page_size),
        }
        try:
            res = requests.post(ALIGO_SMS_LIST_URL, data=payload, timeout=20)
            res.raise_for_status()
            body = res.json()
        except requests.RequestException:
            return {"ok": False, "message": "알리고 상세결과조회 네트워크 오류"}
        except ValueError:
            return {"ok": False, "message": "알리고 상세결과조회 응답 파싱 실패"}

        raws.append(body)
        code = str(body.get("result_code", ""))
        if code != "1":
            return {"ok": False, "message": body.get("message") or "알리고 상세결과조회 실패", "raw": raws}
        rows = body.get("list") or []
        if isinstance(rows, list):
            merged.extend(rows)
        next_yn = str(body.get("next_yn", "N")).upper()
        if next_yn != "Y":
            break
        page += 1

    return {"ok": True, "list": merged, "raw": raws}
