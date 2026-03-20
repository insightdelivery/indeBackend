"""sysCodeManager 테이블(core.SysCodeManager) 기준 존재 여부 검증 — 하위 sid 허용 배열 하드코딩 없음."""

from core.models import SysCodeManager

from .constants import CONTENT_TYPE_PARENT_SID, EVENT_TYPE_PARENT_SID


def is_child_code_valid(parent_sid: str, code_sid: str) -> bool:
    if not code_sid or not parent_sid:
        return False
    return SysCodeManager.objects.filter(
        sysCodeParentsSid=parent_sid,
        sysCodeSid=code_sid,
        sysCodeUse="Y",
    ).exists()


def validate_event_type_code(value: str) -> bool:
    return is_child_code_valid(EVENT_TYPE_PARENT_SID, value)


def validate_content_type_code(value: str) -> bool:
    return is_child_code_valid(CONTENT_TYPE_PARENT_SID, value)
