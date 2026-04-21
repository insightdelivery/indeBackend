"""
사이트 방문 기록 API (siteInputDataPlan.md)
POST /api/site-visits — 인증 불필요, www 루트 비콘에서 호출
"""
from __future__ import annotations

import hashlib
import re
import uuid

from django.conf import settings
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import create_error_response, create_success_response
from sites.public_api.library_useractivity_views import _get_client_ip
from sites.public_api.models import SiteVisitEvent

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_BOT_UA_FRAGMENTS = (
    "kube-probe",
    "googlehc",
    "healthcheck",
    "googlestackdriver",
    "uptimerobot",
    "pingdom",
    "statuscake",
)


def _hash_ip(ip: str) -> str:
    pepper = (getattr(settings, "SECRET_KEY", None) or "inde")[:48]
    raw = f"{pepper}|{ip}|site_visit".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def _channel_from_path(path: str) -> str:
    if not path:
        return SiteVisitEvent.CHANNEL_DIRECT
    low = path.lower()
    if "from_share=1" in low or "from_share=true" in low:
        return SiteVisitEvent.CHANNEL_SHARE_LINK
    if "ref=share" in low:
        return SiteVisitEvent.CHANNEL_SHARE_LINK
    return SiteVisitEvent.CHANNEL_DIRECT


def _is_bot_user_agent(ua: str) -> bool:
    u = (ua or "").lower()
    return any(x in u for x in _BOT_UA_FRAGMENTS) or u.startswith("curl/")


class SiteVisitRecordView(APIView):
    """POST /api/site-visits"""

    permission_classes = [AllowAny]

    def post(self, request):
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:200]
        if _is_bot_user_agent(ua):
            return Response(
                create_success_response({"recorded": False, "reason": "bot"}, message="기록 생략"),
                status=200,
            )

        data = request.data if isinstance(request.data, dict) else {}
        visitor_key = str(data.get("visitorKey") or "").strip()
        path = str(data.get("path") or "").strip()[:400]

        if not visitor_key or not _UUID_RE.match(visitor_key):
            return Response(
                create_error_response("visitorKey(UUID)가 필요합니다."),
                status=400,
            )

        try:
            uuid.UUID(visitor_key)
        except ValueError:
            return Response(
                create_error_response("visitorKey 형식이 올바르지 않습니다."),
                status=400,
            )

        channel = _channel_from_path(path)
        visit_date = timezone.localdate()
        ip = _get_client_ip(request)

        SiteVisitEvent.objects.create(
            visit_date=visit_date,
            channel=channel,
            visitor_key=visitor_key,
            path=path,
            user_agent=ua,
            ip_hash=_hash_ip(ip),
        )
        return Response(
            create_success_response({"recorded": True}, message="방문 기록 완료"),
            status=200,
        )
