"""Hero 배너 전용 이미지 URL — S3 비공개 버킷용 Presigned 변환."""

from __future__ import annotations

import logging
from typing import Optional

from core.s3_storage import S3Storage, get_s3_storage

logger = logging.getLogger(__name__)


def presign_event_banner_image_url(url: Optional[str], expires_in: int = 3600) -> Optional[str]:
    """
    DisplayEvent 배너 이미지 URL을 Presigned URL로 변환한다.

    - 최신 업로드는 `event-banner/` 키를 사용하지만, 기존 데이터는 다른 prefix일 수 있다.
    - 외부 URL까지 무작정 presign하면 잘못된 서명이 될 수 있으므로,
      **S3(amazonaws) URL로 판단되는 경우에만** presign을 시도한다.
    """
    if not url:
        return None
    if url.startswith("data:image"):
        return url
    key = S3Storage.extract_key_from_url(url)
    if not key:
        return url

    # S3 URL(virtual host/path style)인 경우만 presign (외부 링크 보호)
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url.split("?", 1)[0])
        host = (parsed.netloc or "").lower()
        is_s3 = host.startswith("s3.") or (".s3." in host) or host.endswith("amazonaws.com")
        if not is_s3:
            return url
    except Exception:  # noqa: BLE001
        return url

    try:
        s3_storage = get_s3_storage()
        return s3_storage.get_file_url(key, expires_in=expires_in, force_presigned=True)
    except Exception as e:  # noqa: BLE001
        logger.warning("event-banner 이미지 Presigned 실패: %s - %s", key, e)
        return url
