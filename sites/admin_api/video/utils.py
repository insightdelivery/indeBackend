"""
비디오 관련 유틸리티 함수
이미지 처리 및 S3 업로드
"""
import re
import base64
import uuid
from io import BytesIO
from datetime import datetime
from typing import Optional, List
from core.s3_storage import get_s3_storage
from core.s3_storage import S3Storage
import logging

logger = logging.getLogger(__name__)


def get_video_image_path(video_id: int, filename: str = None) -> str:
    """
    비디오 이미지 저장 경로 생성
    
    형식: video/YYYY/MM/{video_id}/{filename}
    
    Args:
        video_id: 비디오 ID
        filename: 파일명 (선택)
    
    Returns:
        S3 경로 문자열
    """
    now = datetime.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    
    path = f"video/{year}/{month}/{video_id}"
    if filename:
        path = f"{path}/{filename}"
    
    return path


def upload_thumbnail_to_s3(thumbnail_data: str, video_id: int) -> Optional[str]:
    """
    썸네일을 S3에 업로드
    
    Args:
        thumbnail_data: base64 인코딩된 이미지 데이터 또는 URL
        video_id: 비디오 ID
    
    Returns:
        업로드된 썸네일의 S3 URL 또는 None (이미 URL인 경우 그대로 반환)
    """
    logger.info(f"upload_thumbnail_to_s3 호출됨. video_id: {video_id}, thumbnail_data 길이: {len(thumbnail_data) if thumbnail_data else 0}")
    
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
        
        # base64 디코딩
        image_bytes = base64.b64decode(base64_data)
        
        # 파일명 생성
        filename = f"thumbnail.{extension}"
        
        # S3 경로 생성
        s3_key = get_video_image_path(video_id, filename)
        
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
        logger.info(f"썸네일 업로드 시작 - video_id: {video_id}, s3_key: {s3_key}, 크기: {len(image_bytes)} bytes")
        url = s3_storage.upload_file(
            file_obj=file_obj,
            key=s3_key,
            content_type=content_type,
            metadata={
                'video_id': str(video_id),
                'image_type': 'thumbnail',
            }
        )
        
        logger.info(f"썸네일 업로드 성공: {s3_key} -> {url}")
        return url
        
    except Exception as e:
        logger.error(f"썸네일 업로드 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def delete_video_images(video_id: int) -> bool:
    """
    비디오 관련 모든 이미지 삭제
    
    Args:
        video_id: 비디오 ID
    
    Returns:
        성공 여부
    """
    try:
        s3_storage = get_s3_storage()
        
        # 비디오 이미지 경로
        prefix = get_video_image_path(video_id)
        
        # 해당 경로의 모든 파일 목록 조회
        files = s3_storage.list_files(prefix=prefix)
        
        # 모든 파일 삭제
        success_count = 0
        for file_key in files:
            if s3_storage.delete_file(file_key):
                success_count += 1
            else:
                logger.warning(f"파일 삭제 실패: {file_key}")
        
        logger.info(f"비디오 {video_id}의 이미지 {success_count}/{len(files)}개 삭제 완료")
        return True
        
    except Exception as e:
        logger.error(f"비디오 이미지 삭제 실패: {e}")
        return False


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
    if key and key.startswith('video/'):
        try:
            s3_storage = get_s3_storage()
            # force_presigned=True로 항상 Presigned URL 생성
            return s3_storage.get_file_url(key, expires_in=expires_in, force_presigned=True)
        except Exception as e:
            logger.warning(f"썸네일 Presigned URL 생성 실패: {key} - {e}")
            return thumbnail_url  # 실패 시 원본 URL 반환
    
    return thumbnail_url  # S3 URL이 아니면 그대로 반환


def upload_attachment_to_s3(file_data: bytes, filename: str, video_id: int) -> Optional[str]:
    """
    첨부파일(강의 자료)을 S3에 업로드
    
    Args:
        file_data: 파일 바이너리 데이터
        filename: 원본 파일명
        video_id: 비디오 ID
    
    Returns:
        업로드된 파일의 S3 URL 또는 None
    """
    try:
        # 파일명에서 확장자 추출
        file_ext = filename.split('.')[-1] if '.' in filename else ''
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # S3 경로 생성
        s3_key = get_video_image_path(video_id, f"attachments/{safe_filename}")
        
        # Content-Type 설정
        content_type_map = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'ppt': 'application/vnd.ms-powerpoint',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        }
        content_type = content_type_map.get(file_ext.lower(), 'application/octet-stream')
        
        # S3에 업로드
        s3_storage = get_s3_storage()
        file_obj = BytesIO(file_data)
        logger.info(f"첨부파일 업로드 시작 - video_id: {video_id}, s3_key: {s3_key}, 크기: {len(file_data)} bytes")
        url = s3_storage.upload_file(
            file_obj=file_obj,
            key=s3_key,
            content_type=content_type,
            metadata={
                'video_id': str(video_id),
                'file_type': 'attachment',
                'original_filename': filename,
            }
        )
        
        logger.info(f"첨부파일 업로드 성공: {s3_key} -> {url}")
        return url
        
    except Exception as e:
        logger.error(f"첨부파일 업로드 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

