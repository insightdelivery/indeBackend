"""
관리자 대시보드 집계 API (방문자 지표 제외 — 프론트 플레이스홀더 유지)
"""
from __future__ import annotations

import logging
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any

from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inquiry.models import Inquiry
from core.utils import create_error_response, create_success_response
from sites.admin_api.articles.models import Article
from sites.admin_api.authentication import AdminJWTAuthentication
from sites.admin_api.menu_codes import MenuCodes
from sites.admin_api.permissions import check_menu_permission
from sites.admin_api.video.models import Video
from sites.public_api.models import PublicMemberShip, SiteVisitEvent

logger = logging.getLogger(__name__)


def _parse_ymd(value: str | None) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _local_today() -> date:
    return timezone.localdate()


def _monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _count_joins_on_day(day: date) -> int:
    return PublicMemberShip.objects.filter(created_at__date=day).count()


def _count_withdrawals_on_day(day: date) -> int:
    return PublicMemberShip.objects.filter(
        status=PublicMemberShip.STATUS_WITHDRAWN,
        withdraw_completed_at__date=day,
    ).count()


def _count_joins_in_range(start: date, end: date) -> int:
    return PublicMemberShip.objects.filter(
        created_at__date__gte=start,
        created_at__date__lte=end,
    ).count()


def _count_withdrawals_in_range(start: date, end: date) -> int:
    return PublicMemberShip.objects.filter(
        status=PublicMemberShip.STATUS_WITHDRAWN,
        withdraw_completed_at__date__gte=start,
        withdraw_completed_at__date__lte=end,
    ).count()


def _member_chart_day(anchor: date) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(13, -1, -1):
        d = anchor - timedelta(days=i)
        label = f"{d.month}/{d.day}"
        rows.append(
            {
                "label": label,
                "joinCount": _count_joins_on_day(d),
                "withdrawCount": _count_withdrawals_on_day(d),
            }
        )
    return rows


def _member_chart_week(anchor: date) -> list[dict[str, Any]]:
    last_monday = _monday_of_week(anchor)
    rows: list[dict[str, Any]] = []
    for i in range(11, -1, -1):
        mon = last_monday - timedelta(weeks=i)
        week_end = mon + timedelta(days=6)
        label = f"{mon.month}/{mon.day}"
        rows.append(
            {
                "label": label,
                "joinCount": _count_joins_in_range(mon, week_end),
                "withdrawCount": _count_withdrawals_in_range(mon, week_end),
            }
        )
    return rows


def _member_chart_month(anchor: date) -> list[dict[str, Any]]:
    """앵커 월을 마지막 달로, 그 전 11개월(총 12개월) — 프론트 Date(y, m - i, 1) 규칙과 동일."""
    rows: list[dict[str, Any]] = []
    end_idx = anchor.year * 12 + (anchor.month - 1)
    for i in range(11, -1, -1):
        idx = end_idx - i
        yy = idx // 12
        mm = idx % 12 + 1
        first = date(yy, mm, 1)
        last = date(yy, mm, monthrange(yy, mm)[1])
        label = f"{yy}.{str(mm).zfill(2)}"
        rows.append(
            {
                "label": label,
                "joinCount": _count_joins_in_range(first, last),
                "withdrawCount": _count_withdrawals_in_range(first, last),
            }
        )
    return rows


def _build_member_chart(granularity: str, anchor: date) -> list[dict[str, Any]]:
    g = (granularity or "month").lower()
    if g == "day":
        return _member_chart_day(anchor)
    if g == "week":
        return _member_chart_week(anchor)
    return _member_chart_month(anchor)


def _aggregate_article() -> dict[str, int]:
    active = Article.objects.filter(deletedAt__isnull=True)
    deleted = Article.objects.filter(deletedAt__isnull=False).count()
    return {
        "total": active.count(),
        "draft": active.filter(status="draft").count(),
        "published": active.filter(status="published").count(),
        "private": active.filter(status="private").count(),
        "scheduled": active.filter(status="scheduled").count(),
        "deleted": deleted,
    }


def _visitor_count_range(start: date, end: date) -> int:
    return SiteVisitEvent.objects.filter(visit_date__gte=start, visit_date__lte=end).count()


def _visitor_today_counts() -> dict[str, int]:
    today = _local_today()
    qs = SiteVisitEvent.objects.filter(visit_date=today)
    return {
        "todayTotal": qs.count(),
        "todayDirect": qs.filter(channel=SiteVisitEvent.CHANNEL_DIRECT).count(),
        "todayShareLink": qs.filter(channel=SiteVisitEvent.CHANNEL_SHARE_LINK).count(),
    }


def _visitor_chart_day(anchor: date) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(13, -1, -1):
        d = anchor - timedelta(days=i)
        label = f"{d.month}/{d.day}"
        rows.append({"label": label, "visitCount": _visitor_count_range(d, d)})
    return rows


def _visitor_chart_week(anchor: date) -> list[dict[str, Any]]:
    last_monday = _monday_of_week(anchor)
    rows: list[dict[str, Any]] = []
    for i in range(11, -1, -1):
        mon = last_monday - timedelta(weeks=i)
        week_end = mon + timedelta(days=6)
        label = f"{mon.month}/{mon.day}"
        rows.append({"label": label, "visitCount": _visitor_count_range(mon, week_end)})
    return rows


def _visitor_chart_month(anchor: date) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    end_idx = anchor.year * 12 + (anchor.month - 1)
    for i in range(11, -1, -1):
        idx = end_idx - i
        yy = idx // 12
        mm = idx % 12 + 1
        first = date(yy, mm, 1)
        last = date(yy, mm, monthrange(yy, mm)[1])
        label = f"{yy}.{str(mm).zfill(2)}"
        rows.append({"label": label, "visitCount": _visitor_count_range(first, last)})
    return rows


def _build_visitor_chart(granularity: str, anchor: date) -> list[dict[str, Any]]:
    g = (granularity or "month").lower()
    if g == "day":
        return _visitor_chart_day(anchor)
    if g == "week":
        return _visitor_chart_week(anchor)
    return _visitor_chart_month(anchor)


def _member_mgmt_card_summary(user: Any) -> dict[str, int]:
    """회원 관리 카드: 당일 last_login 갱신 회원 수(유니크), 미답변 1:1 문의."""
    today_login = 0
    unanswered = 0
    if check_menu_permission(user, MenuCodes.PUBLIC_MEMBERS, "read"):
        today = _local_today()
        today_login = PublicMemberShip.objects.filter(
            last_login__isnull=False,
            last_login__date=today,
        ).count()
    if check_menu_permission(user, MenuCodes.INQUIRY, "read"):
        unanswered = Inquiry.objects.filter(status="waiting").count()
    return {
        "todayLoginMemberCount": today_login,
        "unansweredInquiries": unanswered,
    }


def _aggregate_video(content_type: str) -> dict[str, int]:
    active = Video.objects.filter(contentType=content_type, deletedAt__isnull=True)
    deleted = Video.objects.filter(contentType=content_type, deletedAt__isnull=False).count()
    return {
        "total": active.count(),
        "public": active.filter(status="public").count(),
        "private": active.filter(status="private").count(),
        "scheduled": active.filter(status="scheduled").count(),
        "deleted": deleted,
    }


class DashboardSummaryView(APIView):
    """
    GET /dashboard/summary
    Query:
      - asOf, memberGranularity — 회원 가입·탈퇴 차트
      - visitorAsOf, visitorGranularity — 방문자 추이 차트 (기본: 오늘 / month)
    메뉴 읽기 권한이 있는 블록만 Result에 포함한다. 방문자(siteVisitEvent)는 로그인한 관리자에게 공통 제공.
    """

    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        as_of = _parse_ymd(request.query_params.get("asOf")) or _local_today()
        member_granularity = (request.query_params.get("memberGranularity") or "month").lower()
        if member_granularity not in ("day", "week", "month"):
            member_granularity = "month"

        visitor_as_of = _parse_ymd(request.query_params.get("visitorAsOf")) or _local_today()
        visitor_granularity = (request.query_params.get("visitorGranularity") or "month").lower()
        if visitor_granularity not in ("day", "week", "month"):
            visitor_granularity = "month"

        result: dict[str, Any] = {}

        try:
            if check_menu_permission(user, MenuCodes.PUBLIC_MEMBERS, "read"):
                active_q = Q(status=PublicMemberShip.STATUS_ACTIVE) | Q(
                    status=PublicMemberShip.STATUS_WITHDRAW_REQUEST
                )
                total_active = PublicMemberShip.objects.filter(active_q).count()
                total_withdrawn = PublicMemberShip.objects.filter(
                    status=PublicMemberShip.STATUS_WITHDRAWN
                ).count()
                today = _local_today()
                today_new = PublicMemberShip.objects.filter(created_at__date=today).count()
                today_withdrawn = PublicMemberShip.objects.filter(
                    status=PublicMemberShip.STATUS_WITHDRAWN,
                    withdraw_completed_at__date=today,
                ).count()
                result["members"] = {
                    "totalActive": total_active,
                    "totalWithdrawn": total_withdrawn,
                    "todayNew": today_new,
                    "todayWithdrawn": today_withdrawn,
                    "memberChart": _build_member_chart(member_granularity, as_of),
                }

            if check_menu_permission(user, MenuCodes.INQUIRY, "read"):
                result["inquiries"] = {
                    "unanswered": Inquiry.objects.filter(status="waiting").count(),
                }

            if check_menu_permission(user, MenuCodes.ARTICLE, "read"):
                result["article"] = _aggregate_article()

            if check_menu_permission(user, MenuCodes.VIDEO, "read"):
                result["video"] = _aggregate_video("video")

            if check_menu_permission(user, MenuCodes.SEMINAR, "read"):
                result["seminar"] = _aggregate_video("seminar")

            try:
                tc = _visitor_today_counts()
                result["visitors"] = {
                    "todayTotal": tc["todayTotal"],
                    "todayDirect": tc["todayDirect"],
                    "todayShareLink": tc["todayShareLink"],
                    "visitorChart": _build_visitor_chart(visitor_granularity, visitor_as_of),
                }
            except Exception as visit_exc:
                logger.warning("dashboard visitor aggregate skipped: %s", visit_exc, exc_info=True)
                result["visitors"] = None

            result["memberMgmt"] = _member_mgmt_card_summary(user)

        except Exception as exc:
            logger.exception("dashboard summary failed: %s", exc)
            return Response(
                create_error_response("대시보드 집계 중 오류가 발생했습니다."),
                status=500,
            )

        return Response(create_success_response(result, message="대시보드 집계 조회 성공"))
