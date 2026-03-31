"""
관리자 메뉴 권한 부여 — adminUserPermissionsPlan §5, §6
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from django.db.models import Q, Value
from django.db.models.functions import Coalesce, Lower, Trim

from api.models import AdminMemberShip, UserPermission
from core.models import SysCodeManager
from sites.admin_api.menu_codes import ADMIN_MENU_ROOT

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# 권한 템플릿은 DB 테이블 sysCodeManager(core.SysCodeManager)만 사용한다.
# 대상 행은 관리자 메뉴 루트(ADMIN_MENU_ROOT)의 하위 트리로 한정한다.


def collect_admin_menu_descendant_sids() -> frozenset[str]:
    """
    sysCodeSid = ADMIN_MENU_ROOT 인 행의 **하위 전체**(루트 자신은 제외).
    부모 연결은 sysCodeParentsSid (앞뒤 공백 trim 후 비교).
    """
    rows = SysCodeManager.objects.values_list("sysCodeSid", "sysCodeParentsSid")
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for sid, psid in rows:
        s = (sid or "").strip()
        if not s:
            continue
        p = (psid or "").strip()
        children_by_parent[p].append(s)

    root = ADMIN_MENU_ROOT.strip()
    descendants: set[str] = set()
    frontier = {root}
    while frontier:
        next_frontier: set[str] = set()
        for p in frontier:
            for c in children_by_parent.get(p, []):
                c = (c or "").strip()
                if not c or c == root:
                    continue
                if c not in descendants:
                    descendants.add(c)
                    next_frontier.add(c)
        frontier = next_frontier
    return frozenset(descendants)


def _log_scm_subtree_rows_for_debug(base_qs, role_label: str) -> None:
    """템플릿 0건 시 하위 행의 원본 컬럼 값을 로그(원인 파악용)."""
    rows = list(
        base_qs.order_by("sysCodeSort", "sysCodeName").values(
            "sysCodeSid", "sysCodeVal", "sysCodeVal1", "sysCodeUse"
        )[:200]
    )
    logger.warning(
        "admin_permissions %s_template: 하위에서 Y 매칭 0건 — sysCodeManager 행 샘플(최대 200건)=%s",
        role_label,
        rows,
    )


def _scm_base_qs():
    """공백·NULL 정규화 후 소문자로 비교 (Y/y/공백Y 등)."""
    return SysCodeManager.objects.annotate(
        _v=Lower(Trim(Coalesce("sysCodeVal", Value("")))),
        _v1=Lower(Trim(Coalesce("sysCodeVal1", Value("")))),
        _u=Lower(Trim(Coalesce("sysCodeUse", Value("")))),
    )


def resolve_director_template_qs(desc: frozenset[str] | None = None):
    """
    sysCodeVal=디렉터 템플릿(Y). **ADMIN_MENU_ROOT 하위**만 대상. 엄격→완화 순.
    desc: 미리 구한 하위 sysCodeSid 집합(없으면 내부에서 계산).
    반환: (QuerySet, mode)
    """
    if desc is None:
        desc = collect_admin_menu_descendant_sids()
    if not desc:
        logger.warning(
            "admin_permissions: %s 하위 메뉴가 0건입니다. sysCodeParentsSid 트리를 확인하세요.",
            ADMIN_MENU_ROOT,
        )
        return _scm_base_qs().none(), "no_descendants"

    logger.info(
        "admin_permissions director_template: root=%s descendant_count=%s descendant_sids=%s",
        ADMIN_MENU_ROOT,
        len(desc),
        sorted(desc),
    )

    base = _scm_base_qs().filter(sysCodeSid__in=desc)
    val_y = Q(_v__in=["y", "1"])
    use_on = Q(_u__in=["y", "1"])
    use_on_or_empty = Q(_u__in=["y", "1"]) | Q(_u="")

    strict = base.filter(val_y & use_on)
    if strict.exists():
        matched = list(strict.order_by("sysCodeSort", "sysCodeName").values_list("sysCodeSid", flat=True))
        logger.info(
            "admin_permissions director_template mode=strict matched_sids=%s",
            matched,
        )
        return strict.order_by("sysCodeSort", "sysCodeName"), "strict"

    relaxed = base.filter(val_y & use_on_or_empty)
    if relaxed.exists():
        logger.warning(
            "sysCodeManager director: strict(sysCodeUse 비어 있지 않은 Y/1) 0건 → "
            "sysCodeUse 빈값·NULL 포함해 재조회"
        )
        matched = list(relaxed.order_by("sysCodeSort", "sysCodeName").values_list("sysCodeSid", flat=True))
        logger.info(
            "admin_permissions director_template mode=relaxed_use matched_sids=%s",
            matched,
        )
        return relaxed.order_by("sysCodeSort", "sysCodeName"), "relaxed_use"

    val_only = base.filter(val_y)
    if val_only.exists():
        logger.warning(
            "sysCodeManager director: sysCodeUse 무시하고 sysCodeVal만 Y/1인 행 사용(데이터 점검 권장)"
        )
        matched = list(val_only.order_by("sysCodeSort", "sysCodeName").values_list("sysCodeSid", flat=True))
        logger.info(
            "admin_permissions director_template mode=val_only matched_sids=%s",
            matched,
        )
        return val_only.order_by("sysCodeSort", "sysCodeName"), "val_only"

    # 하위만 대상인 미-annotate 쿼리셋으로 원본 컬럼 덤프
    plain = SysCodeManager.objects.filter(sysCodeSid__in=desc)
    _log_scm_subtree_rows_for_debug(plain, "director")
    return base.none(), "none"


def resolve_editor_template_qs(desc: frozenset[str] | None = None):
    """sysCodeVal1=에디터 템플릿(Y). ADMIN_MENU_ROOT 하위만. 동일 단계."""
    if desc is None:
        desc = collect_admin_menu_descendant_sids()
    if not desc:
        logger.warning(
            "admin_permissions: %s 하위 메뉴가 0건입니다. sysCodeParentsSid 트리를 확인하세요.",
            ADMIN_MENU_ROOT,
        )
        return _scm_base_qs().none(), "no_descendants"

    logger.info(
        "admin_permissions editor_template: root=%s descendant_count=%s descendant_sids=%s",
        ADMIN_MENU_ROOT,
        len(desc),
        sorted(desc),
    )

    base = _scm_base_qs().filter(sysCodeSid__in=desc)
    val_y = Q(_v1__in=["y", "1"])
    use_on = Q(_u__in=["y", "1"])
    use_on_or_empty = Q(_u__in=["y", "1"]) | Q(_u="")

    strict = base.filter(val_y & use_on)
    if strict.exists():
        matched = list(strict.order_by("sysCodeSort", "sysCodeName").values_list("sysCodeSid", flat=True))
        logger.info(
            "admin_permissions editor_template mode=strict matched_sids=%s",
            matched,
        )
        return strict.order_by("sysCodeSort", "sysCodeName"), "strict"

    relaxed = base.filter(val_y & use_on_or_empty)
    if relaxed.exists():
        logger.warning(
            "sysCodeManager editor: strict 0건 → sysCodeUse 빈값·NULL 포함 재조회"
        )
        matched = list(relaxed.order_by("sysCodeSort", "sysCodeName").values_list("sysCodeSid", flat=True))
        logger.info(
            "admin_permissions editor_template mode=relaxed_use matched_sids=%s",
            matched,
        )
        return relaxed.order_by("sysCodeSort", "sysCodeName"), "relaxed_use"

    val_only = base.filter(val_y)
    if val_only.exists():
        logger.warning(
            "sysCodeManager editor: sysCodeUse 무시하고 sysCodeVal1만 Y/1인 행 사용(데이터 점검 권장)"
        )
        matched = list(val_only.order_by("sysCodeSort", "sysCodeName").values_list("sysCodeSid", flat=True))
        logger.info(
            "admin_permissions editor_template mode=val_only matched_sids=%s",
            matched,
        )
        return val_only.order_by("sysCodeSort", "sysCodeName"), "val_only"

    plain = SysCodeManager.objects.filter(sysCodeSid__in=desc)
    _log_scm_subtree_rows_for_debug(plain, "editor")
    return base.none(), "none"


def _template_rows_director():
    qs, _ = resolve_director_template_qs()
    return qs


def _template_rows_editor():
    qs, _ = resolve_editor_template_qs()
    return qs

# 운영 레벨 명칭 — adminUserPermissionsPlan / 메뉴권한 UI
LEVEL_SUPER_ADMIN = 1
LEVEL_DIRECTOR = 5
LEVEL_EDITOR = 6


def assign_default_permissions(user: AdminMemberShip) -> None:
    """
    sysCodeManager 템플릿(sysCodeVal=디렉터, sysCodeVal1=에디터, 값 'Y')으로 user_permissions 행 생성.
    판단은 하지 않음 — 생성만.
    """
    role = (user.admin_role or "editor").lower()
    if role == "director":
        codes = _template_rows_director()
        defaults = {"can_read": True, "can_write": True, "can_delete": True}
    else:
        codes = _template_rows_editor()
        defaults = {"can_read": True, "can_write": True, "can_delete": False}

    count = 0
    for row in codes:
        sid = (row.sysCodeSid or "").strip()
        if not sid:
            continue
        _, created = UserPermission.objects.get_or_create(
            user=user,
            menu_code=sid,
            defaults=defaults,
        )
        if created:
            count += 1
    logger.info(
        "assign_default_permissions: user=%s role=%s rows_created=%s",
        user.memberShipSid,
        role,
        count,
    )


def reapply_level_template_permissions(user: AdminMemberShip) -> dict:
    """
    memberShipLevel에 맞춰 user_permissions를 템플릿으로 **전면 재생성** (§14).
    - 비활성(is_active=False): 템플릿 적용 없이 user_permissions **전부 삭제**
    - L1: 최고관리자 — DB 권한 행 삭제(판단은 레벨 우회)
    - L5: 디렉터 — admin_role=director, sysCodeVal=Y 템플릿
    - L6: 에디터 — admin_role=editor, sysCodeVal1=Y 템플릿
    그 외 레벨은 ValueError.
    """
    user.refresh_from_db()
    level = user.memberShipLevel

    if not user.is_active:
        deleted, _ = UserPermission.objects.filter(user=user).delete()
        logger.info(
            "reapply_level_template_permissions: inactive user=%s cleared_rows=%s",
            user.memberShipSid,
            deleted,
        )
        return {
            "memberShipLevel": level,
            "mode": "inactive_clear",
            "admin_role": user.admin_role or "",
            "rows_created": 0,
            "rows_cleared": int(deleted),
        }

    if level == LEVEL_SUPER_ADMIN:
        deleted, _ = UserPermission.objects.filter(user=user).delete()
        logger.info(
            "reapply_level_template_permissions: super_admin user=%s cleared_rows=%s",
            user.memberShipSid,
            deleted,
        )
        return {
            "memberShipLevel": level,
            "mode": "super_admin",
            "admin_role": user.admin_role or "",
            "rows_created": 0,
            "rows_cleared": int(deleted),
        }

    admin_desc = collect_admin_menu_descendant_sids()

    if level == LEVEL_DIRECTOR:
        role = "director"
        codes_qs, template_match_mode = resolve_director_template_qs(admin_desc)
        defaults = {"can_read": True, "can_write": True, "can_delete": True}
    elif level == LEVEL_EDITOR:
        role = "editor"
        codes_qs, template_match_mode = resolve_editor_template_qs(admin_desc)
        defaults = {"can_read": True, "can_write": True, "can_delete": False}
    else:
        raise ValueError(
            "템플릿 재적용은 회원 레벨 1(최고관리자), 5(디렉터), 6(에디터)만 지원합니다."
        )

    UserPermission.objects.filter(user=user).delete()
    if user.admin_role != role:
        user.admin_role = role
        user.save(update_fields=["admin_role"])

    scm_rows = list(codes_qs)
    scm_matched = len(scm_rows)
    n = 0
    skipped_empty_sid = 0
    for row in scm_rows:
        sid = (row.sysCodeSid or "").strip()
        if not sid:
            skipped_empty_sid += 1
            continue
        UserPermission.objects.create(
            user=user,
            menu_code=sid,
            **defaults,
        )
        n += 1

    if scm_matched > 0 and n == 0 and skipped_empty_sid:
        logger.error(
            "reapply_level_template_permissions: sysCodeManager에서 %s건 매칭했으나 sysCodeSid가 모두 비어 "
            "user_permissions를 채우지 못했습니다. sysCodeSid 컬럼을 확인하세요.",
            scm_matched,
        )

    logger.info(
        "reapply_level_template_permissions: user=%s level=%s role=%s rows=%s mode=%s scm_matched=%s",
        user.memberShipSid,
        level,
        role,
        n,
        template_match_mode,
        scm_matched,
    )
    return {
        "memberShipLevel": level,
        "mode": "template",
        "admin_role": role,
        "rows_created": n,
        "rows_cleared": None,
        "template_match_mode": template_match_mode,
        "scm_template_rows": scm_matched,
        "skipped_empty_sysCodeSid": skipped_empty_sid,
        "admin_menu_root": ADMIN_MENU_ROOT,
        "admin_menu_descendant_count": len(admin_desc),
    }


def build_admin_user_payload(user: AdminMemberShip) -> dict:
    """로그인·토큰 갱신 JSON의 user 객체."""
    base = {
        'memberShipSid': str(user.memberShipSid),
        'memberShipId': user.memberShipId,
        'memberShipName': user.memberShipName,
        'memberShipEmail': user.memberShipEmail,
        'memberShipPhone': user.memberShipPhone or '',
        'memberShipLevel': user.memberShipLevel,
        'is_admin': user.is_admin,
        'admin_role': getattr(user, 'admin_role', '') or 'editor',
        'menu_permissions': serialize_menu_permissions(user),
    }
    return base


def serialize_menu_permissions(user: AdminMemberShip) -> dict:
    """로그인/갱신 응답용 — 프론트 메뉴 필터."""
    if user.memberShipLevel == 1:
        return {"super_admin": True, "items": []}
    items = list(
        UserPermission.objects.filter(user=user).values(
            "menu_code", "can_read", "can_write", "can_delete"
        )
    )
    return {"super_admin": False, "items": items}


def user_can_access_menu(user: AdminMemberShip, menu_code: str, need: str = "read") -> bool:
    """프론트 표시용 (백엔드 최종 판단은 API)."""
    if user.memberShipLevel == 1:
        return True
    try:
        p = UserPermission.objects.get(user=user, menu_code=menu_code)
    except UserPermission.DoesNotExist:
        return False
    if need == "write":
        return p.can_write
    if need == "delete":
        return p.can_delete
    return p.can_read


def fetch_admin_menu_catalog() -> list[dict]:
    """
    ADMIN_MENU_ROOT 하위 트리의 sysCodeManager 행 목록 (루트 자신 제외).
    sysCodeUse=N 인 행은 제외. menu_code=sysCodeSid, label=sysCodeName(비면 코드).
    권한 POST 허용 코드와 동일 소스(adminUserPermissionsPlan §2·§3.1).
    """
    desc = collect_admin_menu_descendant_sids()
    if not desc:
        return []
    qs = (
        SysCodeManager.objects.filter(sysCodeSid__in=desc)
        .exclude(sysCodeUse__iexact="N")
        .order_by("sysCodeSort", "sysCodeSid", "sysCodeName")
    )
    out: list[dict] = []
    for r in qs:
        sid = (r.sysCodeSid or "").strip()
        if not sid:
            continue
        name = (r.sysCodeName or "").strip()
        out.append(
            {
                "menu_code": sid,
                "label": name or sid,
                "sort": r.sysCodeSort,
                "parent_sid": (r.sysCodeParentsSid or "").strip(),
            }
        )
    return out


def allowed_menu_codes_for_permissions() -> frozenset[str]:
    """user_permissions POST 시 menu_code 허용 집합 (DB 하위 트리와 동기화)."""
    return frozenset(item["menu_code"] for item in fetch_admin_menu_catalog())
