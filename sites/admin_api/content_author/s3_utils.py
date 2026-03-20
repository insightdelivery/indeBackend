"""S3 URL 처리 (저자 프로필 등)."""
import logging

from core.s3_storage import get_s3_storage, S3Storage

logger = logging.getLogger(__name__)


def profile_image_to_presigned(url, expires_in=3600):
    """S3 프로필 이미지 URL을 Presigned URL로 변환. content-author/ 경로만 처리."""
    if not url or not isinstance(url, str) or url.strip() == '':
        return url
    if url.startswith('data:'):
        return url
    key = S3Storage.extract_key_from_url(url)
    if not key or not key.startswith('content-author/'):
        return url
    try:
        s3_storage = get_s3_storage()
        return s3_storage.get_file_url(key, expires_in=expires_in, force_presigned=True)
    except Exception as e:
        logger.warning('content_author profile_image presigned 실패: %s - %s', key, e)
        return url
