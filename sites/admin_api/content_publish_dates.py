"""
아티클·비디오/세미나 공통: 발행일시(publishedAt) 규칙.

- 즉시 공개(SYS26209B021): 등록·상태 전환 시점의 now()
- 예약(SYS26209B024): scheduledAt을 발행일시로 저장
"""
from __future__ import annotations

from django.utils import timezone

from sites.admin_api.content_publish_syscodes import STATUS_PUBLISHED, STATUS_SCHEDULED


def published_at_for_create(*, status: str | None, scheduled_at):
    if not status:
        return None
    if status == STATUS_PUBLISHED:
        return timezone.now()
    if status == STATUS_SCHEDULED and scheduled_at:
        return scheduled_at
    return None


def apply_published_at_on_content_update(instance, validated_data: dict) -> None:
    """수정(부분 포함) 시 validated_data에 publishedAt을 넣어 ModelSerializer.update가 반영하도록 한다."""
    new_status = validated_data.get('status', instance.status)
    if 'scheduledAt' in validated_data:
        new_sched = validated_data.get('scheduledAt')
    else:
        new_sched = instance.scheduledAt

    if new_status == STATUS_PUBLISHED:
        if instance.status != STATUS_PUBLISHED:
            validated_data['publishedAt'] = timezone.now()
        elif not getattr(instance, 'publishedAt', None):
            validated_data['publishedAt'] = timezone.now()
        return

    if new_status == STATUS_SCHEDULED and new_sched:
        validated_data['publishedAt'] = new_sched
