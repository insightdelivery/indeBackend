"""
아티클·비디오·세미나 공통 발행 상태 sysCodeSid.

- articleDbPlan.me §2.3.2: SYS26209B021~024 (부모 SYS26209B020).
- 삭제(휴지통 표시용 status 값): SYS26209B025 — 동일 부모 트리에 sysCodeManager 등록 필요.
- 비디오/세미나 `Video.status`도 동일 SID 집합 사용(공개=즉시발행 SID).
"""

from __future__ import annotations

# --- 발행(노출) 계열 (아티클·비디오 공통) ---
STATUS_PUBLISHED = "SYS26209B021"  # 아티클: 즉시발행 / 비디오·세미나: 공개
STATUS_DRAFT = "SYS26209B022"  # 임시저장
STATUS_PRIVATE = "SYS26209B023"  # 비공개
STATUS_SCHEDULED = "SYS26209B024"  # 예약발행
STATUS_DELETED = "SYS26209B025"  # 삭제(휴지통) — soft_delete 시 status에 저장

PUBLISH_STATUS_PARENT = "SYS26209B020"

# 일괄 상태 변경 API 등: 삭제 SID는 별도 삭제 API 사용 — 본 필드만 허용
ARTICLE_STATUS_BATCH_ALLOWED = frozenset(
    {
        STATUS_DRAFT,
        STATUS_PUBLISHED,
        STATUS_PRIVATE,
        STATUS_SCHEDULED,
    }
)

VIDEO_STATUS_BATCH_ALLOWED = frozenset(
    {
        STATUS_DRAFT,
        STATUS_PUBLISHED,
        STATUS_PRIVATE,
        STATUS_SCHEDULED,
    }
)

# 휴지통 목록 API 쿼리(status=) — 레거시 문자열 'deleted' 호환
TRASH_STATUS_QUERY_VALUES = frozenset({"deleted", STATUS_DELETED})


def is_trash_status_filter(value: str | None) -> bool:
    return bool(value) and value in TRASH_STATUS_QUERY_VALUES
