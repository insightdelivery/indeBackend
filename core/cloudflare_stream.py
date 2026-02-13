"""
Cloudflare Stream API 유틸리티
비디오 업로드, 조회, 삭제, 재생 기능 제공
"""
import os
import requests
from typing import Optional, BinaryIO, Dict, Any, List
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CloudflareStream:
    """Cloudflare Stream API 클래스"""
    
    BASE_URL = "https://api.cloudflare.com/client/v4"
    
    def __init__(self):
        """Cloudflare Stream 클라이언트 초기화"""
        # 환경 변수에서 설정 가져오기 (공백 제거)
        self.account_id = os.getenv('CF_ACCOUNT_ID', '').strip()
        self.api_token = os.getenv('CF_STREAM_TOKEN', '').strip()
        
        if not self.account_id:
            raise ValueError(
                "CF_ACCOUNT_ID 환경 변수가 설정되어야 합니다. "
                "Cloudflare Dashboard > My Profile > API Tokens에서 Account ID를 확인하세요."
            )
        if not self.api_token:
            raise ValueError(
                "CF_STREAM_TOKEN 환경 변수가 설정되어야 합니다. "
                "Cloudflare Dashboard > My Profile > API Tokens에서 Stream 권한이 있는 토큰을 생성하세요."
            )
        
        # 디버깅: 환경 변수 로드 확인 (토큰은 일부만 표시)
        logger.info(f"Cloudflare Stream 초기화: Account ID={self.account_id}, Token 길이={len(self.api_token)}")
        
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
        }
    
    def _get_stream_url(self, endpoint: str) -> str:
        """Stream API URL 생성"""
        return f"{self.BASE_URL}/accounts/{self.account_id}/stream{endpoint}"

    def create_tus_upload_session(
        self,
        filename: str,
        filesize: int,
        content_type: str = "video/mp4",
        max_duration_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Cloudflare Stream TUS 업로드 세션 생성
        브라우저가 직접 Cloudflare로 TUS 업로드할 수 있도록 세션을 생성합니다.
        
        Args:
            filename: 파일명
            filesize: 파일 크기 (bytes)
            content_type: 파일 타입 (기본: video/mp4)
            max_duration_seconds: 최대 재생 시간 (초)
        
        Returns:
            {
                "uid": "cloudflare_video_uid",
                "uploadUrl": "tus_upload_location_url"
            }
        """
        import base64
        
        # TUS 메타데이터 생성 (base64 인코딩)
        # Cloudflare Stream은 filename과 name을 모두 지원
        filename_b64 = base64.b64encode(filename.encode('utf-8')).decode('ascii')
        content_type_b64 = base64.b64encode(content_type.encode('utf-8')).decode('ascii')
        # 파일명에서 확장자 제거한 이름도 추가 (Cloudflare가 name으로 사용할 수 있음)
        import os
        name_without_ext = os.path.splitext(filename)[0]
        name_b64 = base64.b64encode(name_without_ext.encode('utf-8')).decode('ascii')
        # filename과 name 모두 전달
        upload_metadata = f"filename {filename_b64},filetype {content_type_b64},name {name_b64}"
        
        # TUS 세션 생성용 헤더
        tus_headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Tus-Resumable': '1.0.0',
            'Upload-Length': str(filesize),
            'Upload-Metadata': upload_metadata,
        }
        
        # 추가 옵션이 있으면 쿼리 파라미터로 전달
        endpoint = self._get_stream_url("")
        params = {'direct_user': 'true'}
        if max_duration_seconds:
            params['maxDurationSeconds'] = max_duration_seconds
        
        logger.info(f"Cloudflare TUS 세션 생성 요청: filename={filename}, filesize={filesize}")
        
        resp = requests.post(
            endpoint,
            headers=tus_headers,
            params=params,
            timeout=30,
        )
        
        # 응답 상세 로깅
        logger.info(f"Cloudflare TUS 세션 생성 응답: Status={resp.status_code}")
        logger.info(f"응답 헤더: {dict(resp.headers)}")
        logger.info(f"응답 본문: {resp.text[:500]}")  # 처음 500자만
        
        if resp.status_code not in [200, 201]:
            try:
                error_body = resp.json()
            except Exception:
                error_body = {}
            
            errors = error_body.get("errors", []) if isinstance(error_body, dict) else []
            messages = error_body.get("messages", []) if isinstance(error_body, dict) else []
            error_codes = {str(e.get("code")) for e in errors if isinstance(e, dict)}
            
            if "10011" in error_codes:
                detail_msg = "Cloudflare Stream 저장 용량이 초과되어 업로드할 수 없습니다."
                if messages:
                    message_texts = [m.get("message") for m in messages if isinstance(m, dict) and m.get("message")]
                    if message_texts:
                        detail_msg = f"{detail_msg} {' / '.join(message_texts)}"
                raise ValueError(detail_msg)
            
            raise ValueError(f"TUS 세션 생성 실패: {resp.status_code} - {resp.text}")
        
        # Location 헤더에서 TUS 업로드 URL 추출
        location = resp.headers.get('Location')
        if not location:
            logger.error(f"Location 헤더가 없습니다. 전체 응답 헤더: {dict(resp.headers)}")
            raise ValueError(f"TUS 세션 생성 응답에 Location 헤더가 없습니다: {dict(resp.headers)}")
        
        logger.info(f"Location 헤더: {location}")
        
        # 응답 본문에서 uid 추출 시도
        video_uid = None
        try:
            result = resp.json()
            logger.info(f"응답 JSON 파싱 성공: {result}")
            
            # 다양한 응답 형식 지원
            if isinstance(result, dict):
                # 형식 1: {"result": {"uid": "..."}}
                if result.get('result') and isinstance(result['result'], dict):
                    video_uid = result['result'].get('uid')
                    logger.info(f"응답에서 uid 추출 (result.uid): {video_uid}")
                
                # 형식 2: {"uid": "..."}
                if not video_uid:
                    video_uid = result.get('uid')
                    logger.info(f"응답에서 uid 추출 (root.uid): {video_uid}")
                
                # 형식 3: {"success": true, "result": {"uid": "..."}}
                if not video_uid and result.get('success') and result.get('result'):
                    if isinstance(result['result'], dict):
                        video_uid = result['result'].get('uid')
                        logger.info(f"응답에서 uid 추출 (success.result.uid): {video_uid}")
        except Exception as e:
            logger.warning(f"응답 JSON 파싱 실패 (무시): {e}")
            logger.warning(f"원본 응답 텍스트: {resp.text[:200]}")
        
        # Location URL에서 uid 추출 시도 (백업)
        if not video_uid and location:
            import re
            # Location 형식 예시:
            # - https://upload.videodelivery.net/{uid}
            # - https://api.cloudflare.com/client/v4/accounts/{account_id}/stream/{uid}
            # - /stream/{uid}
            patterns = [
                r'/([a-f0-9]{32,})$',  # 32자 이상의 hex 문자열 (일반적인 Cloudflare uid)
                r'/([a-f0-9]+)$',      # 모든 hex 문자열
                r'stream/([a-f0-9]+)', # stream/ 뒤의 uid
            ]
            
            for pattern in patterns:
                match = re.search(pattern, location)
                if match:
                    video_uid = match.group(1)
                    logger.info(f"Location URL에서 uid 추출 (패턴: {pattern}): {video_uid}")
                    break
        
        # 여전히 uid를 찾지 못한 경우
        if not video_uid:
            logger.error(f"video uid를 찾을 수 없습니다.")
            logger.error(f"  - Location: {location}")
            logger.error(f"  - 응답 본문: {resp.text}")
            logger.error(f"  - 응답 헤더: {dict(resp.headers)}")
            
            # Location URL 자체를 uploadUrl로 사용하고, uid는 나중에 업로드 완료 후 추출
            # 또는 Location의 마지막 경로를 uid로 사용
            if location:
                import re
                # Location의 마지막 경로를 uid로 사용 (임시)
                last_path = location.rstrip('/').split('/')[-1]
                if last_path and len(last_path) >= 8:  # 최소 길이 체크
                    video_uid = last_path
                    logger.warning(f"Location의 마지막 경로를 uid로 사용 (임시): {video_uid}")
                else:
                    raise ValueError(
                        f"TUS 세션 생성 응답에서 video uid를 찾을 수 없습니다. "
                        f"Location: {location}, 응답 본문: {resp.text[:200]}"
                    )
            else:
                raise ValueError(
                    f"TUS 세션 생성 응답에서 video uid를 찾을 수 없습니다. "
                    f"응답 본문: {resp.text[:200]}"
                )
        
        logger.info(f"Cloudflare TUS 세션 생성 성공: uid={video_uid}, uploadUrl={location}")
        
        return {
            "uid": video_uid,
            "uploadUrl": location,
        }
    
    def create_direct_upload(
        self,
        max_duration_seconds: Optional[int] = None,
        allowed_origins: Optional[list] = None,
        require_signed_urls: bool = False,
        watermark: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Cloudflare Direct Creator Upload URL 발급 (기존 방식, 하위 호환성)
        """
        payload: Dict[str, Any] = {
            "maxDurationSeconds": max_duration_seconds or 36000
        }
        if allowed_origins:
            payload["allowedOrigins"] = allowed_origins
        if require_signed_urls:
            payload["requireSignedURLs"] = True
        if watermark:
            payload["watermark"] = watermark

        # 대용량 업로드(예: 1GB)는 /direct_upload + TUS를 사용해야 안정적이다.
        endpoint = self._get_stream_url("/direct_upload")
        resp = requests.post(
            endpoint,
            headers=self.headers,
            json=payload,
            timeout=30,
        )

        if resp.status_code not in [200, 201]:
            try:
                error_body = resp.json()
            except Exception:
                error_body = {}

            errors = error_body.get("errors", []) if isinstance(error_body, dict) else []
            messages = error_body.get("messages", []) if isinstance(error_body, dict) else []
            error_codes = {str(e.get("code")) for e in errors if isinstance(e, dict)}

            if "10011" in error_codes:
                detail_msg = "Cloudflare Stream 저장 용량이 초과되어 업로드할 수 없습니다."
                if messages:
                    message_texts = [m.get("message") for m in messages if isinstance(m, dict) and m.get("message")]
                    if message_texts:
                        detail_msg = f"{detail_msg} {' / '.join(message_texts)}"
                raise ValueError(detail_msg)

            raise ValueError(f"Direct upload URL 생성 실패(/direct_upload): {resp.status_code} - {resp.text}")

        result = resp.json().get("result") or {}
        upload_url = result.get("uploadURL")
        video_id = result.get("uid")
        if not upload_url or not video_id:
            raise ValueError(f"Direct upload URL 응답 오류: {resp.text}")

        return {
            "upload_url": upload_url,
            "video_id": video_id,
            "raw_result": result,
        }
    
    def upload_video(
        self,
        file_obj: BinaryIO,
        filename: str,
        max_duration_seconds: Optional[int] = None,
        allowed_origins: Optional[list] = None,
        require_signed_urls: bool = False,
        watermark: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        비디오 파일을 Cloudflare Stream에 업로드
        
        Args:
            file_obj: 업로드할 파일 객체 (BinaryIO)
            filename: 파일명
            max_duration_seconds: 최대 재생 시간 (초)
            allowed_origins: 허용된 오리진 리스트
            require_signed_urls: 서명된 URL 필요 여부
            watermark: 워터마크 설정
        
        Returns:
            업로드된 비디오 정보 (video_id 포함)
        """
        try:
            # 파일 크기 확인
            file_obj.seek(0, 2)  # 파일 끝으로 이동
            file_size = file_obj.tell()
            file_obj.seek(0)  # 파일 시작으로 복귀
            
            # 2GB 제한
            MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
            if file_size > MAX_SIZE:
                raise ValueError(f"파일 크기가 2GB를 초과합니다. (현재: {file_size / (1024*1024*1024):.2f}GB)")
            
            # Cloudflare Stream API 직접 업로드 사용
            # direct upload URL은 크기 제한이 있어서, API 엔드포인트로 직접 업로드
            logger.info(f"Cloudflare Stream 비디오 업로드 시작: {filename} ({file_size} bytes)")
            
            # 파일을 다시 읽기 위해 seek
            file_obj.seek(0)
            
            # API 엔드포인트로 직접 업로드 (대용량 파일 지원)
            endpoint = self._get_stream_url("")
            
            # 요청 데이터 준비
            files = {"file": (filename, file_obj, "video/mp4")}
            data = {}
            if max_duration_seconds:
                data["maxDurationSeconds"] = max_duration_seconds
            if allowed_origins:
                data["allowedOrigins"] = allowed_origins
            if require_signed_urls:
                data["requireSignedURLs"] = True
            if watermark:
                data["watermark"] = watermark
            
            max_retries = 3
            retry_delay = 5  # 초
            response = None
            last_error = None
            video_id = None
            
            for attempt in range(max_retries):
                try:
                    # 파일을 다시 읽기 위해 seek (재시도 시 필요)
                    file_obj.seek(0)
                    files = {"file": (filename, file_obj, "video/mp4")}
                    
                    logger.info(f"파일 업로드 시작 (시도 {attempt + 1}/{max_retries}): {filename} -> {endpoint}")
                    # multipart/form-data 업로드를 위해 Content-Type 헤더 제거 (requests가 자동 설정)
                    upload_headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-type'}
                    response = requests.post(
                        endpoint,
                        headers=upload_headers,
                        files=files,
                        data=data,
                        timeout=1800,  # 30분 (2GB 파일 업로드 고려)
                    )
                    logger.info(f"파일 업로드 응답 (시도 {attempt + 1}/{max_retries}): Status={response.status_code}")
                    
                    # 에러 발생 시 상세 정보 로깅
                    if response.status_code not in [200, 201]:
                        logger.error(f"[Cloudflare Stream] 에러 응답 상세:")
                        logger.error(f"  - Status Code: {response.status_code}")
                        logger.error(f"  - 응답 본문: {response.text[:1000]}")  # 처음 1000자만
                        logger.error(f"  - 응답 헤더: {dict(response.headers)}")
                        logger.error(f"  - 요청 URL: {endpoint}")
                        logger.error(f"  - 파일 크기: {file_size} bytes ({file_size / (1024*1024):.2f}MB)")
                        logger.error(f"  - 파일명: {filename}")

                    if response.status_code in [200, 201]:
                        # 성공
                        result = response.json()
                        if result.get('success') and result.get('result'):
                            video_id = result['result'].get('uid')
                            if not video_id:
                                raise ValueError("비디오 ID를 받지 못했습니다.")
                        else:
                            raise ValueError(f"업로드 응답 오류: {result}")
                        break
                    
                    error_text = response.text
                    error_msg = f"비디오 업로드 실패: {response.status_code} - {error_text}"
                    
                    # 502 Bad Gateway는 재시도 가능한 오류
                    if response.status_code == 502:
                        last_error = ValueError(
                            f"Cloudflare Stream 서버 오류(502 Bad Gateway). "
                            f"서버가 일시적으로 응답하지 않습니다. "
                            f"잠시 후 다시 시도해주세요. (시도 {attempt + 1}/{max_retries})"
                        )
                        if attempt < max_retries - 1:
                            logger.warning(f"502 오류 발생, {retry_delay}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                            import time
                            time.sleep(retry_delay)
                            retry_delay *= 2  # 지수 백오프
                            continue
                    elif response.status_code == 413:
                        # 413 오류 상세 분석
                        logger.error(f"[Cloudflare Stream] 413 Payload Too Large 에러 상세 분석:")
                        logger.error(f"  - 전체 응답 본문: {response.text}")
                        logger.error(f"  - 응답 헤더 전체: {dict(response.headers)}")
                        logger.error(f"  - 요청 헤더: {dict(upload_headers)}")
                        logger.error(f"  - 파일 크기: {file_size} bytes ({file_size / (1024*1024):.2f}MB)")
                        logger.error(f"  - 파일명: {filename}")
                        logger.error(f"  - 엔드포인트: {endpoint}")
                        
                        # Cloudflare 응답 파싱 시도
                        try:
                            error_json = response.json()
                            logger.error(f"  - JSON 파싱 성공: {error_json}")
                            cloudflare_error = error_json.get('errors', [{}])[0] if isinstance(error_json.get('errors'), list) else {}
                            cloudflare_message = cloudflare_error.get('message', '')
                            cloudflare_code = cloudflare_error.get('code', '')
                            
                            logger.error(f"  - Cloudflare 에러 코드: {cloudflare_code}")
                            logger.error(f"  - Cloudflare 에러 메시지: {cloudflare_message}")
                            
                            if 'quota' in error_text.lower() or 'minutes' in error_text.lower() or 'allocation' in error_text.lower() or cloudflare_code == '10011':
                                # 실제로 할당량 문제인 경우
                                error_detail = f"Cloudflare Stream 할당량이 초과되었습니다. {cloudflare_message}" if cloudflare_message else "Cloudflare Stream 할당량이 초과되었습니다."
                            else:
                                # 파일 크기 제한 문제 또는 기타 문제
                                file_size_mb = file_size / (1024 * 1024)
                                error_detail = (
                                    f"파일 크기가 Cloudflare Stream 업로드 제한을 초과했습니다. "
                                    f"(파일 크기: {file_size_mb:.2f}MB) "
                                    f"Cloudflare 응답: {cloudflare_message if cloudflare_message else '에러 메시지 없음 (코드: ' + str(cloudflare_code) + ')'}"
                                )
                        except Exception as parse_error:
                            # JSON 파싱 실패 시
                            logger.error(f"  - JSON 파싱 실패: {parse_error}")
                            logger.error(f"  - 원본 응답 텍스트: {response.text}")
                            file_size_mb = file_size / (1024 * 1024)
                            
                            # 응답이 HTML이거나 다른 형식일 수 있음
                            if 'html' in response.text.lower() or '<html' in response.text.lower():
                                error_detail = (
                                    f"413 에러 발생. 응답이 HTML 형식입니다. "
                                    f"이는 Cloudflare가 아닌 중간 프록시나 웹서버에서 발생한 에러일 수 있습니다. "
                                    f"(파일 크기: {file_size_mb:.2f}MB)"
                                )
                            else:
                                error_detail = (
                                    f"파일 크기가 Cloudflare Stream 업로드 제한을 초과했습니다. "
                                    f"(파일 크기: {file_size_mb:.2f}MB) "
                                    f"원본 응답: {response.text[:500]}"
                                )
                        
                        raise ValueError(
                            f"비디오 업로드 실패: 413 Payload Too Large. {error_detail}"
                        )
                    else:
                        raise ValueError(error_msg)
                        
                except requests.exceptions.Timeout:
                    last_error = ValueError(
                        f"비디오 업로드 타임아웃 (30분 초과). "
                        f"파일이 너무 크거나 네트워크가 느립니다. "
                        f"(시도 {attempt + 1}/{max_retries})"
                    )
                    if attempt < max_retries - 1:
                        logger.warning(f"타임아웃 발생, {retry_delay}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                except requests.exceptions.RequestException as e:
                    last_error = ValueError(f"비디오 업로드 중 네트워크 오류: {str(e)}")
                    if attempt < max_retries - 1:
                        logger.warning(f"네트워크 오류 발생, {retry_delay}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
            
            # 모든 재시도 실패 시 마지막 오류 발생
            if not video_id:
                if last_error:
                    raise last_error
                if response:
                    error_text = response.text
                    raise ValueError(f"비디오 업로드 실패: {response.status_code} - {error_text}")
                else:
                    raise ValueError("비디오 업로드 실패: 응답을 받지 못했습니다.")
            
            logger.info(f"비디오 업로드 성공: video_id={video_id}")
            
            # 비디오 정보 조회 (업로드 완료 확인)
            video_info = self.get_video(video_id)
            
            return {
                'video_id': video_id,
                'video_info': video_info,
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Cloudflare Stream API 요청 실패: {e}")
            raise ValueError(f"비디오 업로드 중 오류가 발생했습니다: {str(e)}")
        except Exception as e:
            logger.error(f"비디오 업로드 실패: {e}", exc_info=True)
            raise
    
    def get_video(self, video_id: str) -> Dict[str, Any]:
        """
        비디오 정보 조회
        
        Args:
            video_id: Cloudflare Stream 비디오 ID
        
        Returns:
            비디오 정보
        """
        try:
            endpoint = self._get_stream_url(f"/{video_id}")
            logger.info(f"비디오 정보 조회: {video_id}")
            
            response = requests.get(
                endpoint,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"비디오 조회 실패: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            result = response.json()
            if not result.get('result'):
                error_msg = f"비디오 조회 응답 오류: {result}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            return result['result']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Cloudflare Stream API 요청 실패: {e}")
            raise ValueError(f"비디오 조회 중 오류가 발생했습니다: {str(e)}")
    
    def update_video(self, video_id: str, meta: Optional[Dict[str, Any]] = None, require_signed_urls: Optional[bool] = None, allowed_origins: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        비디오 메타데이터 업데이트
        
        Args:
            video_id: Cloudflare Stream 비디오 ID
            meta: 비디오 메타데이터 (예: {"name": "비디오 이름"})
            require_signed_urls: 서명된 URL 필요 여부
            allowed_origins: 허용된 오리진 리스트
        
        Returns:
            업데이트된 비디오 정보
        """
        try:
            endpoint = self._get_stream_url(f"/{video_id}")
            logger.info(f"비디오 메타데이터 업데이트: {video_id}, meta={meta}")
            
            payload: Dict[str, Any] = {}
            if meta:
                payload['meta'] = meta
            if require_signed_urls is not None:
                payload['requireSignedURLs'] = require_signed_urls
            if allowed_origins:
                payload['allowedOrigins'] = allowed_origins
            
            if not payload:
                logger.warning("업데이트할 메타데이터가 없습니다.")
                return self.get_video(video_id)
            
            logger.info(f"비디오 업데이트 요청: endpoint={endpoint}, payload={payload}")
            
            response = requests.patch(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            logger.info(f"비디오 업데이트 응답: status={response.status_code}, headers={dict(response.headers)}")
            logger.info(f"비디오 업데이트 응답 본문: {response.text[:500]}")
            
            if response.status_code != 200:
                error_msg = f"비디오 업데이트 실패: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            result = response.json()
            logger.info(f"비디오 업데이트 응답 JSON: {result}")
            
            if not result.get('result'):
                error_msg = f"비디오 업데이트 응답 오류: {result}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            updated_result = result['result']
            logger.info(f"비디오 메타데이터 업데이트 성공: {video_id}, meta={updated_result.get('meta')}")
            return updated_result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Cloudflare Stream API 요청 실패: {e}")
            raise ValueError(f"비디오 업데이트 중 오류가 발생했습니다: {str(e)}")
    
    def delete_video(self, video_id: str) -> bool:
        """
        비디오 삭제
        
        Args:
            video_id: Cloudflare Stream 비디오 ID
        
        Returns:
            삭제 성공 여부
        """
        try:
            endpoint = self._get_stream_url(f"/{video_id}")
            logger.info(f"비디오 삭제: {video_id}")
            
            response = requests.delete(
                endpoint,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code not in [200, 204]:
                error_msg = f"비디오 삭제 실패: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False
            
            logger.info(f"비디오 삭제 성공: {video_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Cloudflare Stream API 요청 실패: {e}")
            return False
    
    def get_video_embed_url(self, video_id: str) -> str:
        """
        비디오 임베드 URL 생성
        
        Args:
            video_id: Cloudflare Stream 비디오 ID
        
        Returns:
            임베드 URL
        """
        return f"https://iframe.videodelivery.net/{video_id}"
    
    def get_video_thumbnail_url(self, video_id: str, thumbnail_id: str = "thumbnail.jpg") -> str:
        """
        비디오 썸네일 URL 생성
        
        Args:
            video_id: Cloudflare Stream 비디오 ID
            thumbnail_id: 썸네일 ID (기본값: thumbnail.jpg)
        
        Returns:
            썸네일 URL
        """
        return f"https://videodelivery.net/{video_id}/thumbnails/{thumbnail_id}"
    
    def get_video_hls_url(self, video_id: str) -> str:
        """
        비디오 HLS 스트리밍 URL 생성
        
        Args:
            video_id: Cloudflare Stream 비디오 ID
        
        Returns:
            HLS URL
        """
        return f"https://videodelivery.net/{video_id}/manifest/video.m3u8"
    
    def get_video_dash_url(self, video_id: str) -> str:
        """
        비디오 DASH 스트리밍 URL 생성
        
        Args:
            video_id: Cloudflare Stream 비디오 ID
        
        Returns:
            DASH URL
        """
        return f"https://videodelivery.net/{video_id}/manifest/video.mpd"


def get_cloudflare_stream() -> CloudflareStream:
    """
    Cloudflare Stream 인스턴스 생성 (싱글톤 패턴)
    
    Returns:
        CloudflareStream 인스턴스
    """
    return CloudflareStream()

