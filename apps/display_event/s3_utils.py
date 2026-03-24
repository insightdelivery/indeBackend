"""Hero 배너 전용 이미지 URL — S3 비공개 버킷용 Presigned 변환."""

from __future__ import annotations

import logging
from typing import Optional

from core.s3_storage import S3Storage, get_s3_storage

logger = logging.getLogger(__name__)


def presign_event_banner_image_url(url: Optional[str], expires_in: int = 3600) -> Optional[str]:
    """
    `event-banner/` 키로 올린 배너 이미지에 대해 Presigned URL 반환.
    그 외 URL(기존 데이터·콘텐츠 썸네일 등)은 그대로 둔다.
    """
    if not url:
        return None
    if url.startswith("data:image"):
        return url
    key = S3Storage.extract_key_from_url(url)
    if not key or not key.startswith("event-banner/"):
        return url
    try:
        s3_storage = get_s3_storage()
        return s3_storage.get_file_url(key, expires_in=expires_in, force_presigned=True)
    except Exception as e:  # noqa: BLE001
        logger.warning("event-banner 이미지 Presigned 실패: %s - %s", key, e)
        return url
