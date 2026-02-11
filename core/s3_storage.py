"""
AWS S3 파일 저장소 유틸리티
등록, 수정, 삭제, 보기 기능 제공
"""
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from django.conf import settings
from typing import Optional, BinaryIO
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class S3Storage:
    """AWS S3 파일 저장소 클래스"""
    
    def __init__(self):
        """S3 클라이언트 초기화"""
        # Django settings에서 먼저 확인, 없으면 환경 변수에서 가져오기
        try:
            from django.conf import settings
            self.aws_access_key_id = getattr(settings, 'AWS_ACCESS_KEY_ID', None) or os.getenv('AWS_ACCESS_KEY_ID')
            self.aws_secret_access_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None) or os.getenv('AWS_SECRET_ACCESS_KEY')
            self.aws_region = getattr(settings, 'AWS_S3_REGION_NAME', None) or os.getenv('AWS_S3_REGION_NAME', 'ap-northeast-2')
        except Exception:
            # Django가 로드되지 않은 경우 환경 변수에서 직접 가져오기
            self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
            self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            self.aws_region = os.getenv('AWS_S3_REGION_NAME', 'ap-northeast-2')
        
        self.bucket_name = self._get_bucket_name()
        
        # 상세한 에러 메시지 제공
        missing_vars = []
        if not self.aws_access_key_id:
            missing_vars.append('AWS_ACCESS_KEY_ID')
        if not self.aws_secret_access_key:
            missing_vars.append('AWS_SECRET_ACCESS_KEY')
        
        if missing_vars:
            error_msg = f"다음 환경 변수가 설정되어야 합니다: {', '.join(missing_vars)}"
            # 디버깅을 위해 현재 환경 변수 상태 로깅
            logger.error(f"S3 초기화 실패: {error_msg}")
            logger.error(f"현재 AWS_ACCESS_KEY_ID 존재 여부: {bool(os.getenv('AWS_ACCESS_KEY_ID'))}")
            logger.error(f"현재 AWS_SECRET_ACCESS_KEY 존재 여부: {bool(os.getenv('AWS_SECRET_ACCESS_KEY'))}")
            raise ValueError(error_msg)
        
        if not self.bucket_name:
            raise ValueError("AWS_STORAGE_BUCKET_NAME이 설정되어야 합니다.")
        
        # 버킷 정보 로깅 (프로덕션 디버깅용)
        logger.info(f"S3 Storage 초기화 완료 - 버킷: {self.bucket_name}, 리전: {self.aws_region}")
        
        # S3 클라이언트 생성 (Config를 사용하여 리전과 서명 버전 명시)
        from botocore.config import Config
        config = Config(
            region_name=self.aws_region,
            signature_version='s3v4',
            # Presigned URL을 regional endpoint + path style로 고정해
            # 글로벌 endpoint 리다이렉트로 인한 서명 불일치를 방지한다.
            s3={'addressing_style': 'path'}
        )
        
        # 명시적으로 Regional Endpoint URL 설정
        # Boto3가 글로벌 엔드포인트(s3.amazonaws.com)를 사용하여 서명 불일치 문제가 발생할 수 있음
        # ap-northeast-2 등 리전별 엔드포인트를 강제 사용
        endpoint_url = f"https://s3.{self.aws_region}.amazonaws.com"
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region,
            endpoint_url=endpoint_url,
            config=config
        )
    
    def _get_bucket_name(self) -> str:
        """환경에 따라 버킷 이름 반환"""
        try:
            from django.conf import settings
            # Django settings에서 먼저 확인
            explicit_bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None) or os.getenv('AWS_STORAGE_BUCKET_NAME')
            if explicit_bucket:
                logger.info(f"명시적 버킷 이름 사용: {explicit_bucket}")
                return explicit_bucket
            
            # DEBUG 모드에 따라 버킷 구분
            django_debug = os.getenv('DJANGO_DEBUG', '0')
            settings_debug = getattr(settings, 'DEBUG', True)
            is_production = (
                django_debug == '0' or 
                not settings_debug
            )
            
            logger.info(f"환경 판단 - DJANGO_DEBUG: {django_debug}, settings.DEBUG: {settings_debug}, is_production: {is_production}")
            
            if is_production:
                bucket_name = (
                    getattr(settings, 'AWS_STORAGE_BUCKET_NAME_PRODUCTION', None) or 
                    os.getenv('AWS_STORAGE_BUCKET_NAME_PRODUCTION', 'inde-production')
                )
                logger.info(f"프로덕션 버킷 선택: {bucket_name}")
            else:
                bucket_name = (
                    getattr(settings, 'AWS_STORAGE_BUCKET_NAME_DEVELOPMENT', None) or 
                    os.getenv('AWS_STORAGE_BUCKET_NAME_DEVELOPMENT', 'inde-develope')
                )
                logger.info(f"개발 버킷 선택: {bucket_name}")
            
            return bucket_name
        except Exception as e:
            logger.error(f"버킷 이름 가져오기 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Django가 로드되지 않은 경우 환경 변수에서 직접 가져오기
            explicit_bucket = os.getenv('AWS_STORAGE_BUCKET_NAME')
            if explicit_bucket:
                return explicit_bucket
            
            is_production = os.getenv('DJANGO_DEBUG', '0') == '0'
            if is_production:
                return os.getenv('AWS_STORAGE_BUCKET_NAME_PRODUCTION', 'inde-production')
            else:
                return os.getenv('AWS_STORAGE_BUCKET_NAME_DEVELOPMENT', 'inde-develope')
    
    def _get_s3_url(self, key: str) -> str:
        """S3 파일 URL 생성"""
        # CloudFront 또는 커스텀 도메인이 있는 경우 사용
        custom_domain = os.getenv('AWS_S3_CUSTOM_DOMAIN')
        if custom_domain:
            return f"https://{custom_domain}/{key}"
        
        # 기본 S3 URL
        return f"https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/{key}"
    
    def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        파일을 S3에 업로드
        
        Args:
            file_obj: 업로드할 파일 객체 (BinaryIO)
            key: S3에 저장될 파일 경로/이름
            content_type: 파일의 MIME 타입 (예: 'image/jpeg')
            metadata: 추가 메타데이터 (dict)
        
        Returns:
            업로드된 파일의 URL
        
        Raises:
            ClientError: S3 업로드 실패 시
            NoCredentialsError: AWS 인증 정보가 없을 때
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if metadata:
                extra_args['Metadata'] = metadata
            
            # 파일을 처음으로 되돌림 (이미 읽힌 경우 대비)
            file_obj.seek(0)
            
            logger.info(f"S3 업로드 시도 - 버킷: {self.bucket_name}, 키: {key}, 크기: {file_obj.getvalue().__len__() if hasattr(file_obj, 'getvalue') else 'unknown'} bytes")
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs=extra_args if extra_args else None
            )
            
            url = self._get_s3_url(key)
            logger.info(f"파일 업로드 성공: {key} -> {url}")
            return url
            
        except NoCredentialsError:
            logger.error("AWS 인증 정보가 없습니다.")
            raise ValueError("AWS 인증 정보가 설정되지 않았습니다.")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"S3 업로드 실패 - 버킷: {self.bucket_name}, 키: {key}, 에러 코드: {error_code}, 메시지: {error_message}")
            logger.error(f"전체 에러 응답: {e.response}")
            import traceback
            logger.error(traceback.format_exc())
            raise Exception(f"파일 업로드 실패 (버킷: {self.bucket_name}, 키: {key}): {error_code} - {error_message}")
    
    def upload_file_from_path(
        self,
        file_path: str,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        로컬 파일 경로에서 S3로 업로드
        
        Args:
            file_path: 로컬 파일 경로
            key: S3에 저장될 파일 경로/이름
            content_type: 파일의 MIME 타입
            metadata: 추가 메타데이터
        
        Returns:
            업로드된 파일의 URL
        """
        try:
            with open(file_path, 'rb') as file_obj:
                return self.upload_file(file_obj, key, content_type, metadata)
        except FileNotFoundError:
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        except Exception as e:
            logger.error(f"파일 업로드 실패: {e}")
            raise
    
    def download_file(self, key: str, local_path: str) -> bool:
        """
        S3에서 파일 다운로드
        
        Args:
            key: S3 파일 경로/이름
            local_path: 저장할 로컬 파일 경로
        
        Returns:
            성공 여부 (bool)
        """
        try:
            self.s3_client.download_file(self.bucket_name, key, local_path)
            logger.info(f"파일 다운로드 성공: {key} -> {local_path}")
            return True
        except ClientError as e:
            logger.error(f"S3 다운로드 실패: {e}")
            return False
    
    def get_file_url(self, key: str, expires_in: int = 3600, force_presigned: bool = False) -> str:
        """
        파일 URL 가져오기 (Presigned URL 또는 공개 URL)
        
        Args:
            key: S3 파일 경로/이름
            expires_in: Presigned URL 만료 시간 (초, 기본 1시간)
            force_presigned: True인 경우 항상 Presigned URL 생성 (기본: False)
        
        Returns:
            파일 URL
        """
        try:
            # force_presigned가 True인 경우 항상 Presigned URL 생성
            if force_presigned:
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': key},
                    ExpiresIn=expires_in
                )
                logger.debug(f"Presigned URL 생성 (force_presigned=True): {key} -> {url[:100]}...")
                return url
            
            # force_presigned가 False인 경우에도 보안을 위해 Presigned URL 생성
            # (버킷이 비공개로 설정되어 있을 수 있으므로)
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )
            logger.debug(f"Presigned URL 생성: {key} -> {url[:100]}...")
            return url
        except Exception as e:
            logger.error(f"파일 URL 생성 실패: {key} - {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def delete_file(self, key: str) -> bool:
        """
        S3에서 파일 삭제
        
        Args:
            key: 삭제할 파일의 S3 경로/이름
        
        Returns:
            성공 여부 (bool)
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"파일 삭제 성공: {key}")
            return True
        except ClientError as e:
            logger.error(f"S3 삭제 실패: {e}")
            return False
    
    def file_exists(self, key: str) -> bool:
        """
        파일 존재 여부 확인
        
        Args:
            key: 확인할 파일의 S3 경로/이름
        
        Returns:
            존재 여부 (bool)
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
    
    def get_file_info(self, key: str) -> Optional[dict]:
        """
        파일 정보 가져오기
        
        Args:
            key: 파일의 S3 경로/이름
        
        Returns:
            파일 정보 (크기, 타입, 수정일 등) 또는 None
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return {
                'size': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError:
            return None
    
    def list_files(self, prefix: str = '', max_keys: int = 1000) -> list:
        """
        특정 경로의 파일 목록 가져오기
        
        Args:
            prefix: 파일 경로 접두사 (예: 'images/')
            max_keys: 최대 반환 개수
        
        Returns:
            파일 키 목록 (list)
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
        except ClientError as e:
            logger.error(f"파일 목록 조회 실패: {e}")
            return []
    
    @staticmethod
    def extract_key_from_url(url: str) -> Optional[str]:
        """
        S3 URL에서 파일 키 추출
        
        Args:
            url: S3 파일 URL (Presigned URL 포함)
        
        Returns:
            파일 키 또는 None
        """
        try:
            # S3 URL 형식:
            # 1. Virtual Host Style: https://bucket.s3.region.amazonaws.com/key
            # 2. Path Style (endpoint_url 사용시): https://s3.region.amazonaws.com/bucket/key
            # 3. Custom Domain: https://custom-domain.com/key
            # 4. Presigned URL: 위 형식 + ?X-Amz-Algorithm=... (쿼리 파라미터)
            
            from urllib.parse import urlparse, unquote
            # 쿼리 파라미터 제거 (Presigned URL 처리)
            url_without_query = url.split('?')[0]
            parsed = urlparse(url_without_query)
            
            path = parsed.path.lstrip('/')
            path = unquote(path)
            
            # Path Style URL 처리 (Host가 s3. 으로 시작하면 Path Style일 가능성이 높음)
            # 예: s3.ap-northeast-2.amazonaws.com/bucket-name/article/...
            if parsed.netloc.startswith('s3.'):
                parts = path.split('/', 1)
                if len(parts) > 1:
                    # 첫 번째 부분은 버킷 이름이므로 제외하고 키만 반환
                    return parts[1]
            
            # Virtual Host Style URL 처리
            # 예: bucket.s3.region.amazonaws.com/article/...
            if '.s3.' in parsed.netloc:
                # path가 이미 키이므로 그대로 반환
                return path if path else None
            
            return path if path else None
        except Exception as e:
            logger.error(f"URL에서 키 추출 실패: {url}, 에러: {e}")
            return None


# 싱글톤 인스턴스
_s3_storage_instance = None


def get_s3_storage() -> S3Storage:
    """S3Storage 싱글톤 인스턴스 반환"""
    global _s3_storage_instance
    if _s3_storage_instance is None:
        _s3_storage_instance = S3Storage()
    return _s3_storage_instance

