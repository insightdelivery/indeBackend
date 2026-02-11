"""
아티클 관련 유틸리티 함수
이미지 처리 및 S3 업로드
"""
import re
import base64
import uuid
from io import BytesIO
from datetime import datetime
from typing import Tuple, List, Optional
from core.s3_storage import get_s3_storage
from core.s3_storage import S3Storage
import logging

logger = logging.getLogger(__name__)


def get_article_image_path(article_id: int, filename: str = None) -> str:
    """
    아티클 이미지 저장 경로 생성
    
    형식: article/YYYY/MM/{article_id}/{filename}
    
    Args:
        article_id: 아티클 ID
        filename: 파일명 (선택)
    
    Returns:
        S3 경로 문자열
    """
    now = datetime.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    
    path = f"article/{year}/{month}/{article_id}"
    if filename:
        path = f"{path}/{filename}"
    
    return path


def extract_base64_images(html_content: str) -> List[Tuple[str, str, str]]:
    """
    HTML 본문에서 base64 이미지 추출
    
    Args:
        html_content: HTML 본문 내용
    
    Returns:
        [(전체 img 태그, base64 데이터, 확장자), ...] 리스트
    """
    if not html_content:
        return []
    
    # base64 이미지 패턴: <img src="data:image/...;base64,..." ...>
    pattern = r'<img[^>]+src="data:image/([^;]+);base64,([^"]+)"[^>]*>'
    matches = re.finditer(pattern, html_content, re.IGNORECASE)
    
    images = []
    for match in matches:
        full_tag = match.group(0)
        extension = match.group(1)  # jpeg, png, gif 등
        base64_data = match.group(2)
        images.append((full_tag, base64_data, extension))
    
    return images


def upload_base64_image_to_s3(
    base64_data: str,
    extension: str,
    article_id: int,
    image_type: str = 'content',
    image_index: int = 0
) -> Optional[str]:
    """
    base64 이미지를 S3에 업로드
    
    Args:
        base64_data: base64 인코딩된 이미지 데이터
        extension: 이미지 확장자 (jpeg, png, gif 등)
        article_id: 아티클 ID
        image_type: 이미지 타입 ('content' 또는 'thumbnail')
        image_index: 이미지 인덱스 (본문 내 여러 이미지 구분용)
    
    Returns:
        업로드된 이미지의 S3 URL 또는 None
    """
    try:
        # base64 디코딩
        image_bytes = base64.b64decode(base64_data)
        
        # 파일명 생성
        if image_type == 'thumbnail':
            filename = f"thumbnail.{extension}"
        else:
            filename = f"image_{image_index}.{extension}"
        
        # S3 경로 생성
        s3_key = get_article_image_path(article_id, filename)
        
        # Content-Type 설정
        content_type_map = {
            'jpeg': 'image/jpeg',
            'jpg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
        }
        content_type = content_type_map.get(extension.lower(), 'image/jpeg')
        
        # S3에 업로드
        s3_storage = get_s3_storage()
        file_obj = BytesIO(image_bytes)
        logger.info(f"이미지 업로드 시작 - article_id: {article_id}, image_type: {image_type}, s3_key: {s3_key}, 크기: {len(image_bytes)} bytes")
        url = s3_storage.upload_file(
            file_obj=file_obj,
            key=s3_key,
            content_type=content_type,
            metadata={
                'article_id': str(article_id),
                'image_type': image_type,
            }
        )
        
        logger.info(f"이미지 업로드 성공: {s3_key} -> {url}")
        return url
        
    except Exception as e:
        logger.error(f"이미지 업로드 실패 - article_id: {article_id}, image_type: {image_type}, s3_key: {s3_key}, 에러: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def replace_base64_images_with_s3_urls(html_content: str, article_id: int) -> Tuple[str, List[str]]:
    """
    HTML 본문의 base64 이미지를 S3 URL로 교체
    
    Args:
        html_content: HTML 본문 내용
        article_id: 아티클 ID
    
    Returns:
        (교체된 HTML 내용, 업로드된 이미지 S3 키 리스트)
    """
    if not html_content:
        return html_content, []
    
    images = extract_base64_images(html_content)
    if not images:
        return html_content, []
    
    uploaded_keys = []
    new_content = html_content
    
    for index, (full_tag, base64_data, extension) in enumerate(images):
        # S3에 업로드
        s3_url = upload_base64_image_to_s3(
            base64_data=base64_data,
            extension=extension,
            article_id=article_id,
            image_type='content',
            image_index=index
        )
        
        if s3_url:
            # S3 키 추출 (나중에 삭제하기 위해)
            key = S3Storage.extract_key_from_url(s3_url)
            if key:
                uploaded_keys.append(key)
            
            # img 태그의 src를 S3 URL로 교체
            new_img_tag = re.sub(
                r'src="data:image/[^"]+"',
                f'src="{s3_url}"',
                full_tag
            )
            new_content = new_content.replace(full_tag, new_img_tag)
            logger.info(f"이미지 교체 완료: {full_tag[:50]}... -> {s3_url}")
        else:
            logger.warning(f"이미지 업로드 실패, 원본 유지: {full_tag[:50]}...")
    
    return new_content, uploaded_keys


def upload_thumbnail_to_s3(thumbnail_data: str, article_id: int) -> Optional[str]:
    """
    썸네일을 S3에 업로드
    
    Args:
        thumbnail_data: base64 인코딩된 이미지 데이터 또는 URL
        article_id: 아티클 ID
    
    Returns:
        업로드된 썸네일의 S3 URL 또는 None (이미 URL인 경우 그대로 반환)
    """
    logger.info(f"upload_thumbnail_to_s3 호출됨. article_id: {article_id}, thumbnail_data 길이: {len(thumbnail_data) if thumbnail_data else 0}")
    
    if not thumbnail_data:
        logger.warning("썸네일 데이터가 없습니다.")
        return None
    
    # 이미 URL인 경우 그대로 반환
    if not thumbnail_data.startswith('data:image'):
        logger.info(f"썸네일이 이미 URL입니다. 길이: {len(thumbnail_data)}")
        return thumbnail_data if len(thumbnail_data) <= 500 else None
    
    try:
        # base64 데이터 추출
        match = re.match(r'data:image/([^;]+);base64,(.+)', thumbnail_data)
        if not match:
            logger.error("base64 데이터 형식이 올바르지 않습니다.")
            return None
        
        extension = match.group(1)
        base64_data = match.group(2)
        logger.info(f"base64 데이터 추출 성공. 확장자: {extension}, 데이터 길이: {len(base64_data)}")
        
        # S3에 업로드
        s3_url = upload_base64_image_to_s3(
            base64_data=base64_data,
            extension=extension,
            article_id=article_id,
            image_type='thumbnail',
            image_index=0
        )
        
        if s3_url:
            logger.info(f"썸네일 업로드 성공: {s3_url}")
        else:
            logger.error("썸네일 업로드 실패: upload_base64_image_to_s3가 None을 반환했습니다.")
        
        return s3_url
        
    except Exception as e:
        logger.error(f"썸네일 업로드 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def delete_article_images(article_id: int) -> bool:
    """
    아티클 관련 모든 이미지 삭제
    
    Args:
        article_id: 아티클 ID
    
    Returns:
        성공 여부
    """
    try:
        s3_storage = get_s3_storage()
        
        # 아티클 이미지 경로
        prefix = get_article_image_path(article_id)
        
        # 해당 경로의 모든 파일 목록 조회
        files = s3_storage.list_files(prefix=prefix)
        
        # 모든 파일 삭제
        success_count = 0
        for file_key in files:
            if s3_storage.delete_file(file_key):
                success_count += 1
            else:
                logger.warning(f"파일 삭제 실패: {file_key}")
        
        logger.info(f"아티클 {article_id}의 이미지 {success_count}/{len(files)}개 삭제 완료")
        return True
        
    except Exception as e:
        logger.error(f"아티클 이미지 삭제 실패: {e}")
        return False


def extract_s3_keys_from_content(html_content: str) -> List[str]:
    """
    HTML 본문에서 S3 이미지 키 추출
    
    Args:
        html_content: HTML 본문 내용
    
    Returns:
        S3 키 리스트
    """
    if not html_content:
        return []
    
    keys = []
    # S3 URL 패턴: 따옴표(Single/Double) 모두 지원
    # r'<img[^>]*?src=["\']([^"\']+?)["\'][^>]*?>'
    pattern = r'<img[^>]*?src=["\']([^"\']+?)["\'][^>]*?>'
    matches = re.finditer(pattern, html_content, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        url = match.group(1)
        if url and not url.startswith('data:image'):
            key = S3Storage.extract_key_from_url(url)
            # key가 None이거나 비어있을 수 있음
            if key and key.startswith('article/'):
                keys.append(key)
    
    return keys


def convert_s3_urls_to_presigned(html_content: str, expires_in: int = 3600) -> str:
    """
    HTML 본문의 S3 이미지 URL을 Presigned URL로 변환
    
    Args:
        html_content: HTML 본문 내용
        expires_in: Presigned URL 만료 시간 (초, 기본 1시간)
    
    Returns:
        Presigned URL로 변환된 HTML 본문
    """
    if not html_content:
        return html_content
    
    # logger.info(f"convert_s3_urls_to_presigned 호출됨. HTML 길이: {len(html_content)}")
    
    # S3 URL 패턴: 따옴표(Single/Double) 모두 지원
    # Group 0: Full tag
    # Group 1: Attributes before src
    # Group 2: Quote char (single or double)
    # Group 3: URL
    # Group 4: Attributes after src
    pattern = r'<img\s+([^>]*?)src=(["\'])(.*?)\2([^>]*?)>'
    
    matches = list(re.finditer(pattern, html_content, flags=re.IGNORECASE | re.DOTALL))
    # logger.info(f"이미지 태그 발견: {len(matches)}개")
    
    if not matches:
        return html_content
    
    def replace_url(match):
        full_match = match.group(0)
        attrs_before = match.group(1)
        # quote = match.group(2)
        url = match.group(3)
        attrs_after = match.group(4)
        
        # logger.info(f"처리 중인 이미지 URL: {url[:100]}...")
        
        # base64 이미지는 그대로 유지
        if url.startswith('data:image'):
            return full_match
        
        # S3 URL인 경우 Presigned URL로 변환
        key = S3Storage.extract_key_from_url(url)
        # logger.info(f"추출된 S3 키: {key}")
        
        if key and key.startswith('article/'):
            try:
                s3_storage = get_s3_storage()
                # force_presigned=True로 항상 Presigned URL 생성
                presigned_url = s3_storage.get_file_url(key, expires_in=expires_in, force_presigned=True)
                
                # 태그 재구성 (Standardize to double quotes for output)
                # 공백 처리: attrs_before가 비어있지 않고 공백으로 끝나지 않으면 공백 추가?
                # 보통 regex \s+ 가 포함되어 있지 않으므로 attrs_before가 바로 붙음.
                # 원본 태그 구조: <img[attrs_before]src=[quote][url][quote][attrs_after]>
                # attrs_before가 없으면 <img src=...>이므로 img뒤에 바로 붙음.
                # 하지만 HTML 표준상 img 뒤에 공백이 있어야 함.
                # regex에서 <img\s+ ...> 로 했으므로, \s+는 매칭되지 않은 leading space가 있음.
                # 아, regex: <img\s+([^>]*?)...
                # \s+ is OUTSIDE the group 1. So Group 1 starts AFTER the space.
                # So we must add ' ' manually or capture the space.
                
                # Re-check regex: pattern = r'<img\s+([^>]*?)src=(["\'])(.*?)\2([^>]*?)>'
                # Match: <img ...>
                # The \s+ consumes the space. It is NOT in group 1.
                # So we need to put it back: f'<img {attrs_before}src="{presigned_url}"{attrs_after}>'
                
                new_img_tag = f'<img {attrs_before}src="{presigned_url}"{attrs_after}>'
                return new_img_tag
            except Exception as e:
                logger.error(f"Presigned URL 생성 실패: {key} - {e}")
                import traceback
                logger.error(traceback.format_exc())
                return full_match  # 실패 시 원본 URL 유지
        
        return full_match  # S3 URL이 아니면 그대로 유지
    
    new_content = re.sub(pattern, replace_url, html_content, flags=re.IGNORECASE | re.DOTALL)
    
    return new_content


def get_presigned_thumbnail_url(thumbnail_url: str, expires_in: int = 3600) -> Optional[str]:
    """
    썸네일 URL을 Presigned URL로 변환
    
    Args:
        thumbnail_url: 썸네일 URL
        expires_in: Presigned URL 만료 시간 (초, 기본 1시간)
    
    Returns:
        Presigned URL 또는 None
    """
    if not thumbnail_url:
        return None
    
    # base64 이미지는 그대로 반환
    if thumbnail_url.startswith('data:image'):
        return thumbnail_url
    
    # S3 URL인 경우 Presigned URL로 변환
    key = S3Storage.extract_key_from_url(thumbnail_url)
    if key and key.startswith('article/'):
        try:
            s3_storage = get_s3_storage()
            # force_presigned=True로 항상 Presigned URL 생성
            return s3_storage.get_file_url(key, expires_in=expires_in, force_presigned=True)
        except Exception as e:
            logger.warning(f"썸네일 Presigned URL 생성 실패: {key} - {e}")
            return thumbnail_url  # 실패 시 원본 URL 반환
    
    return thumbnail_url  # S3 URL이 아니면 그대로 반환

