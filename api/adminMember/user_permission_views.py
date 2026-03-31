"""
관리자별 user_permissions CRUD — adminUserPermissionsPlan.md §13
"""
from __future__ import annotations

import logging

from django.db import IntegrityError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import AdminMemberShip, UserPermission
from api.services.admin_permissions import (
    allowed_menu_codes_for_permissions,
    fetch_admin_menu_catalog,
    reapply_level_template_permissions,
)
from core.models import AuditLog
from sites.admin_api.authentication import AdminJWTAuthentication
from sites.admin_api.menu_codes import ADMIN_MENU_ROOT, MenuCodes
from sites.admin_api.permissions import MenuPermission

logger = logging.getLogger(__name__)


def _request_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class UserPermissionReapplyTemplateView(APIView):
    """
    POST: 대상 관리자의 현재 memberShipLevel에 맞춰 sysCodeManager 템플릿으로 user_permissions 재생성.
    비활성(is_active=False) 관리자는 user_permissions 전부 삭제만 수행.
    활성 중 레벨 1·5·6만 템플릿 재적용 (그 외 400).
    """

    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.MENU_PERMISSION

    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "user_id가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(request.user, AdminMemberShip):
            return Response(
                {"error": "이 API는 관리자 회원(AdminMemberShip)만 사용할 수 있습니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            target = AdminMemberShip.objects.get(memberShipSid=user_id)
        except AdminMemberShip.DoesNotExist:
            return Response({"error": "관리자를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        try:
            result = reapply_level_template_permissions(target)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.objects.create(
            user_id=str(request.user.memberShipSid),
            site_slug="admin_api",
            action="update",
            resource="user_permissions",
            resource_id=f"reapply_template:{target.memberShipSid}",
            ip_address=_request_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            details={
                "target_user_id": str(target.memberShipSid),
                "reapply": result,
            },
        )

        return Response({"result": result}, status=status.HTTP_200_OK)


class AdminMenuCatalogView(APIView):
    """
    GET: ADMIN_MENU_ROOT 하위 sysCodeManager 메뉴 목록 (코드·표시명).
    프론트 메뉴권한 UI·라벨 해석의 단일 소스.
    """

    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.MENU_PERMISSION

    def get(self, request):
        items = fetch_admin_menu_catalog()
        return Response(
            {
                "admin_menu_root": ADMIN_MENU_ROOT,
                "items": items,
            },
            status=status.HTTP_200_OK,
        )


class UserPermissionListCreateView(APIView):
    """
    GET: ?user_id= — 해당 관리자의 메뉴 권한 목록
    POST: user_permissions 행 생성
    """

    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.MENU_PERMISSION

    def get(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "user_id 쿼리 파라미터가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(request.user, AdminMemberShip):
            return Response(
                {"error": "이 API는 관리자 회원(AdminMemberShip)만 사용할 수 있습니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            target = AdminMemberShip.objects.get(memberShipSid=user_id)
        except AdminMemberShip.DoesNotExist:
            return Response({"error": "관리자를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        rows = UserPermission.objects.filter(user=target).order_by("menu_code")
        permissions = [
            {
                "id": p.id,
                "menu_code": p.menu_code,
                "can_read": p.can_read,
                "can_write": p.can_write,
                "can_delete": p.can_delete,
            }
            for p in rows
        ]
        return Response(
            {
                "target_user": {
                    "memberShipSid": str(target.memberShipSid),
                    "memberShipId": target.memberShipId,
                    "memberShipName": target.memberShipName,
                    "memberShipLevel": target.memberShipLevel,
                    "is_active": target.is_active,
                },
                "permissions": permissions,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        if not isinstance(request.user, AdminMemberShip):
            return Response(
                {"error": "이 API는 관리자 회원(AdminMemberShip)만 사용할 수 있습니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user_id = request.data.get("user_id")
        menu_code = request.data.get("menu_code")
        if not user_id or not menu_code:
            return Response(
                {"error": "user_id와 menu_code는 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed = allowed_menu_codes_for_permissions()
        if menu_code not in allowed:
            return Response(
                {
                    "error": f"허용되지 않은 menu_code입니다: {menu_code}. "
                    f"관리자 메뉴 루트({ADMIN_MENU_ROOT}) 하위·사용 중인 sysCodeManager 행만 가능합니다.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target = AdminMemberShip.objects.get(memberShipSid=user_id)
        except AdminMemberShip.DoesNotExist:
            return Response({"error": "관리자를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        can_read = bool(request.data.get("can_read", True))
        can_write = bool(request.data.get("can_write", False))
        can_delete = bool(request.data.get("can_delete", False))

        try:
            obj = UserPermission.objects.create(
                user=target,
                menu_code=menu_code,
                can_read=can_read,
                can_write=can_write,
                can_delete=can_delete,
            )
        except IntegrityError:
            return Response(
                {"error": "이미 해당 메뉴 코드에 대한 권한이 있습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        AuditLog.objects.create(
            user_id=str(request.user.memberShipSid),
            site_slug="admin_api",
            action="create",
            resource="user_permissions",
            resource_id=str(obj.id),
            ip_address=self._client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            details={
                "target_user_id": str(target.memberShipSid),
                "menu_code": menu_code,
            },
        )

        return Response(
            {
                "permission": {
                    "id": obj.id,
                    "menu_code": obj.menu_code,
                    "can_read": obj.can_read,
                    "can_write": obj.can_write,
                    "can_delete": obj.can_delete,
                }
            },
            status=status.HTTP_201_CREATED,
        )

    def _client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class UserPermissionDetailView(APIView):
    """PUT: 권한 행 수정 / DELETE: 권한 행 삭제"""

    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.MENU_PERMISSION

    def put(self, request, pk):
        if not isinstance(request.user, AdminMemberShip):
            return Response(
                {"error": "이 API는 관리자 회원(AdminMemberShip)만 사용할 수 있습니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # select_related("user")는 user_id·memberShipSid collation 불일치 시 MySQL 1267을 유발할 수 있음
        try:
            obj = UserPermission.objects.get(pk=pk)
        except UserPermission.DoesNotExist:
            return Response({"error": "권한 행을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        if "can_read" in request.data:
            obj.can_read = bool(request.data["can_read"])
        if "can_write" in request.data:
            obj.can_write = bool(request.data["can_write"])
        if "can_delete" in request.data:
            obj.can_delete = bool(request.data["can_delete"])

        obj.save()

        AuditLog.objects.create(
            user_id=str(request.user.memberShipSid),
            site_slug="admin_api",
            action="update",
            resource="user_permissions",
            resource_id=str(obj.id),
            ip_address=self._client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            details={
                "target_user_id": str(obj.user_id),
                "menu_code": obj.menu_code,
            },
        )

        return Response(
            {
                "permission": {
                    "id": obj.id,
                    "menu_code": obj.menu_code,
                    "can_read": obj.can_read,
                    "can_write": obj.can_write,
                    "can_delete": obj.can_delete,
                }
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        if not isinstance(request.user, AdminMemberShip):
            return Response(
                {"error": "이 API는 관리자 회원(AdminMemberShip)만 사용할 수 있습니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            obj = UserPermission.objects.get(pk=pk)
        except UserPermission.DoesNotExist:
            return Response({"error": "권한 행을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        target_sid = str(obj.user_id)
        menu_code = obj.menu_code
        obj.delete()

        AuditLog.objects.create(
            user_id=str(request.user.memberShipSid),
            site_slug="admin_api",
            action="delete",
            resource="user_permissions",
            resource_id=str(pk),
            ip_address=self._client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            details={"target_user_id": target_sid, "menu_code": menu_code},
        )

        return Response({"message": "삭제되었습니다."}, status=status.HTTP_200_OK)

    def _client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
