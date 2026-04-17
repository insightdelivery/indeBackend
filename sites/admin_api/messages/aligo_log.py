"""알리고 발송 요청 본문 로깅(운영 디버깅용)."""
from __future__ import annotations

import copy
import logging
from typing import Any
from urllib.parse import urlencode

from django.conf import settings

logger = logging.getLogger(__name__)


def _mask_secret(value: str, *, head: int = 3, tail: int = 2) -> str:
    v = value or ""
    if not v:
        return ""
    if len(v) <= head + tail + 1:
        return "***"
    return f"{v[:head]}…{v[-tail:]}"


def log_aligo_form_outbound(url: str, payload: dict[str, Any], *, channel: str) -> None:
    """
    requests.post(..., data=payload) 로 나가는 내용과 동일한 application/x-www-form-urlencoded 본문을 로그에 남긴다.
    - 기본: apikey·key·senderkey 만 마스킹, 나머지(수신번호·제목·본문·button_1 등)는 그대로.
    - settings.ALIGO_LOG_FULL_OUTBOUND 가 참이면 비밀값도 그대로 로그(저장소·권한에 유의).
    """
    full = bool(getattr(settings, "ALIGO_LOG_FULL_OUTBOUND", False))
    safe: dict[str, Any] = copy.deepcopy(payload)
    if not full:
        if "apikey" in safe and safe["apikey"]:
            safe["apikey"] = _mask_secret(str(safe["apikey"]), head=4, tail=4)
        if "key" in safe and safe["key"]:
            safe["key"] = _mask_secret(str(safe["key"]), head=4, tail=4)
        if "senderkey" in safe and safe["senderkey"]:
            safe["senderkey"] = _mask_secret(str(safe["senderkey"]), head=6, tail=4)
    # 값은 모두 str 로 직렬화 (urlencode)
    flat = {k: "" if v is None else str(v) for k, v in safe.items()}
    body = urlencode(flat)
    logger.info("aligo_send channel=%s url=%s outbound=%s", channel, url, body)
