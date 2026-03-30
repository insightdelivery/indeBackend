"""
관리자용 PublicMemberShip CRUD API (AdminJWT) + 탈퇴/복구
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from core.models import AuditLog
from sites.admin_api.authentication import AdminJWTAuthentication
from sites.admin_api.menu_codes import MenuCodes
from sites.admin_api.permissions import MenuPermission
from sites.public_api.models import PublicMemberShip
from .serializers import (
    PublicMemberListSerializer,
    PublicMemberDetailSerializer,
    PublicMemberCreateUpdateSerializer,
)


class PublicMemberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminPublicMemberViewSet(viewsets.ModelViewSet):
    """관리자 공개 회원(PublicMemberShip) CRUD + 탈퇴/복구"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.PUBLIC_MEMBERS
    queryset = PublicMemberShip.objects.all()
    pagination_class = PublicMemberPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["email", "name", "nickname", "phone"]
    ordering_fields = ["member_sid", "email", "created_at", "last_login", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter in (PublicMemberShip.STATUS_ACTIVE, PublicMemberShip.STATUS_WITHDRAWN, PublicMemberShip.STATUS_WITHDRAW_REQUEST):
            qs = qs.filter(status=status_filter)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PublicMemberListSerializer
        if self.action == "retrieve":
            return PublicMemberDetailSerializer
        return PublicMemberCreateUpdateSerializer

    def _get_client_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        """관리자 탈퇴 처리: status=WITHDRAWN, is_active=False (Soft Delete)"""
        member = self.get_object()
        if member.status == PublicMemberShip.STATUS_WITHDRAWN:
            return Response(
                {"detail": "이미 탈퇴 처리된 회원입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = request.data.get("reason") or ""
        detail_reason = request.data.get("detail_reason") or ""
        member.status = PublicMemberShip.STATUS_WITHDRAWN
        member.is_active = False
        member.withdraw_completed_at = timezone.now()
        member.withdraw_reason = reason or member.withdraw_reason
        member.withdraw_detail_reason = detail_reason or member.withdraw_detail_reason
        member.withdraw_ip = self._get_client_ip(request)
        member.withdraw_user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:500]
        member.save(update_fields=[
            "status", "is_active", "withdraw_completed_at",
            "withdraw_reason", "withdraw_detail_reason",
            "withdraw_ip", "withdraw_user_agent", "updated_at",
        ])
        AuditLog.objects.create(
            user_id=str(request.user.memberShipSid) if getattr(request.user, "memberShipSid", None) else "admin",
            site_slug="admin_api",
            action="update",
            resource="publicMemberShip",
            resource_id=str(member.member_sid),
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            details={"action": "withdraw", "member_sid": member.member_sid},
        )
        return Response(
            {"detail": "탈퇴 처리되었습니다.", "member_sid": member.member_sid},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """탈퇴 회원 정상 복구: status=ACTIVE, is_active=True, 탈퇴 필드 초기화"""
        member = self.get_object()
        if member.status != PublicMemberShip.STATUS_WITHDRAWN:
            return Response(
                {"detail": "탈퇴된 회원만 복구할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        member.status = PublicMemberShip.STATUS_ACTIVE
        member.is_active = True
        member.withdraw_reason = None
        member.withdraw_detail_reason = None
        member.withdraw_requested_at = None
        member.withdraw_completed_at = None
        member.withdraw_ip = None
        member.withdraw_user_agent = None
        member.save(update_fields=[
            "status", "is_active",
            "withdraw_reason", "withdraw_detail_reason",
            "withdraw_requested_at", "withdraw_completed_at",
            "withdraw_ip", "withdraw_user_agent", "updated_at",
        ])
        AuditLog.objects.create(
            user_id=str(request.user.memberShipSid) if getattr(request.user, "memberShipSid", None) else "admin",
            site_slug="admin_api",
            action="update",
            resource="publicMemberShip",
            resource_id=str(member.member_sid),
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            details={"action": "withdraw_restore", "member_sid": member.member_sid},
        )
        return Response(
            {"detail": "정상 회원으로 복구되었습니다.", "member_sid": member.member_sid},
            status=status.HTTP_200_OK,
        )
