"""
관리자 메뉴 권한 — adminUserPermissionsPlan.md §7, §18
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Sequence, Union

from django.contrib.auth.models import AnonymousUser
from rest_framework.permissions import BasePermission

from api.models import AdminMemberShip, UserPermission
from core.models import Account

logger = logging.getLogger(__name__)

# Super Admin: memberShipLevel == 1 (문서 §18.3)
SUPER_ADMIN_LEVEL = 1

MenuCodeType = Union[str, None]
MenuCodesArg = Union[str, Sequence[str], None]


def http_method_to_action(method: str) -> str:
    """§18.1 HTTP Method → action"""
    m = (method or "GET").upper()
    if m == "GET" or m == "HEAD":
        return "read"
    if m in ("POST", "PUT", "PATCH"):
        return "write"
    if m == "DELETE":
        return "delete"
    if m == "OPTIONS":
        return "read"
    return "read"


def _is_super_admin_user(user: Any) -> bool:
    if user is None or isinstance(user, AnonymousUser):
        return False
    if isinstance(user, AdminMemberShip):
        return user.memberShipLevel == SUPER_ADMIN_LEVEL
    if isinstance(user, Account):
        return bool(getattr(user, "is_superuser", False) or getattr(user, "is_staff", False))
    return False


def check_menu_permission(
    user: Any,
    menu_code: str,
    action: str = "read",
) -> bool:
    """
    user_permissions만으로 판단 (§16). sysCode Y/N으로 판단 금지.
    """
    if user is None or isinstance(user, AnonymousUser):
        return False
    if _is_super_admin_user(user):
        return True
    if not isinstance(user, AdminMemberShip):
        return False

    perm = UserPermission.objects.filter(
        user=user,
        menu_code=menu_code,
    ).first()
    if not perm:
        return False
    field = f"can_{action}"
    return bool(getattr(perm, field, False))


def check_any_menu_permission(
    user: Any,
    menu_codes: Sequence[str],
    action: str = "read",
) -> bool:
    """여러 menu_code 중 하나라도 허용이면 True (비디오/세미나 공용 API 등)."""
    if user is None or isinstance(user, AnonymousUser):
        return False
    if _is_super_admin_user(user):
        return True
    if not isinstance(user, AdminMemberShip):
        return False
    for mc in menu_codes:
        if check_menu_permission(user, mc, action):
            return True
    return False


def resolve_menu_codes(view: Any, request) -> Optional[Sequence[str]]:
    """View에서 menu_code 또는 menu_codes 또는 get_menu_code(request) 해석."""
    if hasattr(view, "get_menu_code"):
        getter = getattr(view, "get_menu_code")
        if callable(getter):
            code = getter(request)
            if code is None:
                return None
            if isinstance(code, (list, tuple)):
                return code
            return [code]
    codes = getattr(view, "menu_codes", None)
    if codes:
        return codes if isinstance(codes, (list, tuple)) else (codes,)
    single = getattr(view, "menu_code", None)
    if single:
        return [single]
    return None


class MenuPermission(BasePermission):
    """
    View에 menu_code 또는 menu_codes 설정.
    둘 다 없으면 True (인증만 다른 클래스에서 처리).
    """

    def has_permission(self, request, view) -> bool:
        codes = resolve_menu_codes(view, request)
        if not codes:
            return True

        user = request.user
        action = http_method_to_action(request.method)

        if len(codes) == 1:
            allowed = check_menu_permission(user, codes[0], action)
        else:
            allowed = check_any_menu_permission(user, codes, action)

        if not allowed:
            uid = getattr(user, "memberShipSid", None) or getattr(user, "pk", None)
            logger.warning(
                "Permission denied: user=%s, menu=%s, action=%s",
                uid,
                ",".join(codes),
                action,
            )
        return allowed
