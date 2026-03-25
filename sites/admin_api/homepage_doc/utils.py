"""
홈페이지 정적 문서 HTML 내 base64 이미지 → S3 URL (PUT 시에만 호출, wwwDocEtc.md §7)
"""
import re
import base64
import uuid
import logging
from io import BytesIO
from datetime import datetime
from typing import Optional

from core.s3_storage import get_s3_storage
from sites.admin_api.articles.utils import extract_base64_images

logger = logging.getLogger(__name__)


def _homepage_doc_s3_key(extension: str) -> str:
    now = datetime.now()
    name = f"{uuid.uuid4().hex}.{extension}"
    return f"homepage-doc/{now:%Y/%m}/{name}"


def _upload_base64_homepage_image(base64_data: str, extension: str) -> Optional[str]:
    try:
        image_bytes = base64.b64decode(base64_data)
        s3_key = _homepage_doc_s3_key(extension)
        content_type_map = {
            'jpeg': 'image/jpeg',
            'jpg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
        }
        content_type = content_type_map.get(extension.lower(), 'image/jpeg')
        s3_storage = get_s3_storage()
        file_obj = BytesIO(image_bytes)
        url = s3_storage.upload_file(
            file_obj=file_obj,
            key=s3_key,
            content_type=content_type,
            metadata={'source': 'homepage_doc_info'},
        )
        return url
    except Exception as e:
        logger.error('homepage_doc S3 업로드 실패: %s', e, exc_info=True)
        return None


def replace_base64_images_in_homepage_html(html_content: str) -> str:
    """본문의 data:image base64 img를 S3 URL로 치환. 실패 시 해당 태그는 원본 유지."""
    if not html_content:
        return html_content or ''

    images = extract_base64_images(html_content)
    if not images:
        return html_content

    new_content = html_content
    for full_tag, base64_data, extension in images:
        s3_url = _upload_base64_homepage_image(base64_data, extension)
        if s3_url:
            new_img_tag = re.sub(
                r'src="data:image/[^"]+"',
                f'src="{s3_url}"',
                full_tag,
            )
            new_content = new_content.replace(full_tag, new_img_tag)
        else:
            logger.warning('homepage_doc 이미지 업로드 실패, 원본 유지')

    return new_content
