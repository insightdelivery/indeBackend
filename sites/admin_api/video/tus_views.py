"""
TUS (Resumable Upload Protocol) 서버 구현
비디오 파일을 청크 단위로 업로드하고 재개 가능한 업로드 지원
"""
import os
import uuid
import json
import time
import base64
from pathlib import Path
from typing import Optional, Dict, Any
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from sites.admin_api.authentication import AdminJWTAuthentication
from core.cloudflare_stream import get_cloudflare_stream
from core.utils import create_success_response, create_error_response
import logging

logger = logging.getLogger(__name__)

# 업로드 세션 저장 디렉토리
def get_tus_upload_dir():
    """TUS 업로드 디렉토리 경로 반환"""
    if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
        base_dir = Path(settings.MEDIA_ROOT)
    else:
        # MEDIA_ROOT가 없으면 프로젝트 루트의 media 디렉토리 사용
        base_dir = Path(__file__).resolve().parent.parent.parent.parent / 'media'
    
    tus_dir = base_dir / 'tus_uploads'
    tus_dir.mkdir(parents=True, exist_ok=True)
    return tus_dir

TUS_UPLOAD_DIR = get_tus_upload_dir()
TUS_METADATA_DIR = TUS_UPLOAD_DIR / 'metadata'
TUS_METADATA_DIR.mkdir(parents=True, exist_ok=True)

# 업로드 세션 타임아웃 (24시간)
TUS_UPLOAD_TIMEOUT = 24 * 60 * 60


@method_decorator(csrf_exempt, name='dispatch')
class TUSUploadView(View):
    """
    TUS 프로토콜 업로드 뷰
    POST: 업로드 생성
    HEAD: 업로드 상태 확인
    PATCH: 청크 업로드
    """
    
    def dispatch(self, request, *args, **kwargs):
        """인증 확인 (OPTIONS 요청은 제외)"""
        # OPTIONS 요청은 인증 없이 처리 (CORS preflight)
        if request.method == 'OPTIONS':
            return self.options(request, *args, **kwargs)
        
        # Authorization 헤더 확인 (모든 가능한 헤더 이름 확인)
        auth_header = (
            request.META.get('HTTP_AUTHORIZATION', '') or
            request.META.get('Authorization', '') or
            (request.headers.get('Authorization', '') if hasattr(request, 'headers') else '')
        )
        
        # 요청 헤더 전체 로깅 (디버깅용)
        logger.info(f"[TUS] {request.method} 요청 - URL: {request.path}")
        logger.info(f"[TUS] Authorization 헤더: {auth_header[:50] if auth_header else '없음'}...")
        logger.debug(f"[TUS] 모든 HTTP_* 헤더: {[k for k in request.META.keys() if k.startswith('HTTP_')]}")
        
        # AdminJWTAuthentication 적용
        auth = AdminJWTAuthentication()
        try:
            result = auth.authenticate(request)
            if result is None:
                logger.warning(f"[TUS] 인증 실패: Authorization 헤더가 없거나 형식이 올바르지 않습니다.")
                logger.debug(f"[TUS] 요청 META 키: {list(request.META.keys())[:20]}")
                response = HttpResponse('Unauthorized: Missing or invalid Authorization header', status=401)
                self._add_cors_headers(response, request)
                return response
            
            user, token = result
            if not user:
                logger.warning(f"[TUS] 인증 실패: 사용자를 찾을 수 없습니다.")
                response = HttpResponse('Unauthorized: User not found', status=401)
                self._add_cors_headers(response, request)
                return response
            
            request.user = user
            logger.info(f"[TUS] 인증 성공: user={user}")
        except Exception as e:
            logger.error(f"[TUS] 인증 실패: {e}", exc_info=True)
            response = HttpResponse(f'Unauthorized: {str(e)}', status=401)
            self._add_cors_headers(response, request)
            return response
        
        response = super().dispatch(request, *args, **kwargs)
        # 모든 응답에 CORS 헤더 추가
        if isinstance(response, HttpResponse):
            self._add_cors_headers(response, request)
        return response
    
    def _add_cors_headers(self, response: HttpResponse, request):
        """CORS 헤더 추가"""
        from django.conf import settings
        
        # Origin 헤더 확인
        origin = request.META.get('HTTP_ORIGIN', '')
        
        # CORS_ALLOWED_ORIGINS 확인
        if hasattr(settings, 'CORS_ALLOWED_ORIGINS') and origin in settings.CORS_ALLOWED_ORIGINS:
            response['Access-Control-Allow-Origin'] = origin
        elif hasattr(settings, 'CORS_ALLOW_ALL_ORIGINS') and settings.CORS_ALLOW_ALL_ORIGINS:
            response['Access-Control-Allow-Origin'] = '*'
        else:
            # 기본값으로 요청한 Origin 허용
            if origin:
                response['Access-Control-Allow-Origin'] = origin
            else:
                response['Access-Control-Allow-Origin'] = '*'
        
        response['Access-Control-Allow-Methods'] = 'POST, HEAD, PATCH, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Upload-Length, Upload-Metadata, Upload-Offset, Content-Type, Authorization, Origin, X-Requested-With'
        response['Access-Control-Expose-Headers'] = 'Location, Upload-Expires, Upload-Offset, Upload-Length, Upload-Metadata, Tus-Resumable'
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Max-Age'] = '86400'
    
    def post(self, request, upload_id: Optional[str] = None):
        """
        TUS 업로드 생성 (POST)
        
        Headers:
        - Upload-Length: 전체 파일 크기 (필수)
        - Upload-Metadata: 메타데이터 (base64 인코딩, 선택)
        
        Response:
        - 201 Created
        - Location: 업로드 URL
        - Upload-Expires: 만료 시간
        """
        try:
            # Upload-Length 헤더 확인
            upload_length = request.META.get('HTTP_UPLOAD_LENGTH')
            if not upload_length:
                return HttpResponse('Missing Upload-Length header', status=400)
            
            try:
                upload_length = int(upload_length)
            except ValueError:
                return HttpResponse('Invalid Upload-Length', status=400)
            
            # 2GB 제한
            MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
            if upload_length > MAX_SIZE:
                return HttpResponse(
                    f'File size exceeds maximum limit (2GB). Current: {upload_length / (1024*1024*1024):.2f}GB',
                    status=413
                )
            
            # 업로드 ID 생성
            if not upload_id:
                upload_id = str(uuid.uuid4())
            
            # 메타데이터 파싱
            upload_metadata = request.META.get('HTTP_UPLOAD_METADATA', '')
            metadata = {}
            if upload_metadata:
                try:
                    # TUS 메타데이터 형식: key1 value1,key2 value2 (base64 인코딩)
                    for item in upload_metadata.split(','):
                        if ' ' in item:
                            key, value = item.split(' ', 1)
                            # base64 디코딩
                            try:
                                decoded_value = base64.b64decode(value).decode('utf-8')
                                metadata[key] = decoded_value
                            except Exception:
                                metadata[key] = value
                except Exception as e:
                    logger.warning(f"메타데이터 파싱 실패: {e}")
            
            # 파일명 확인
            filename = metadata.get('filename', f'video_{upload_id}.mp4')
            
            # 업로드 파일 경로
            upload_file_path = TUS_UPLOAD_DIR / f'{upload_id}.bin'
            metadata_file_path = TUS_METADATA_DIR / f'{upload_id}.json'
            
            # 메타데이터 저장
            created_at = time.time()
            metadata_data = {
                'upload_id': upload_id,
                'filename': filename,
                'upload_length': upload_length,
                'upload_offset': 0,
                'metadata': metadata,
                'created_at': created_at,
            }
            
            with open(metadata_file_path, 'w') as f:
                json.dump(metadata_data, f)
            
            # 빈 파일 생성 (또는 기존 파일 확인)
            if not upload_file_path.exists():
                upload_file_path.touch()
                # 파일 생성 시간 설정
                os.utime(upload_file_path, (created_at, created_at))
            
            # 응답 헤더 설정
            expires_at = int(time.time()) + TUS_UPLOAD_TIMEOUT
            response = HttpResponse(status=201)
            response['Location'] = f'/video/upload/tus/{upload_id}'
            response['Upload-Expires'] = str(expires_at)
            response['Tus-Resumable'] = '1.0.0'
            
            logger.info(f"[TUS] 업로드 생성: upload_id={upload_id}, filename={filename}, size={upload_length}")
            
            return response
            
        except Exception as e:
            logger.error(f"[TUS] 업로드 생성 실패: {e}", exc_info=True)
            return HttpResponse(f'Internal Server Error: {str(e)}', status=500)
    
    def head(self, request, upload_id: str):
        """
        TUS 업로드 상태 확인 (HEAD)
        
        Response:
        - 200 OK
        - Upload-Offset: 현재 업로드된 바이트 수
        - Upload-Length: 전체 파일 크기
        - Upload-Metadata: 메타데이터
        """
        try:
            metadata_file_path = TUS_METADATA_DIR / f'{upload_id}.json'
            upload_file_path = TUS_UPLOAD_DIR / f'{upload_id}.bin'
            
            if not metadata_file_path.exists():
                return HttpResponse('Upload not found', status=404)
            
            # 메타데이터 로드
            with open(metadata_file_path, 'r') as f:
                metadata_data = json.load(f)
            
            # 현재 파일 크기 확인
            if upload_file_path.exists():
                upload_offset = upload_file_path.stat().st_size
            else:
                upload_offset = 0
            
            # 메타데이터 업데이트
            metadata_data['upload_offset'] = upload_offset
            with open(metadata_file_path, 'w') as f:
                json.dump(metadata_data, f)
            
            # 응답 헤더 설정
            response = HttpResponse(status=200)
            response['Upload-Offset'] = str(upload_offset)
            response['Upload-Length'] = str(metadata_data['upload_length'])
            response['Tus-Resumable'] = '1.0.0'
            
            # 메타데이터 재구성
            upload_metadata = []
            for key, value in metadata_data.get('metadata', {}).items():
                encoded_value = base64.b64encode(str(value).encode('utf-8')).decode('utf-8')
                upload_metadata.append(f'{key} {encoded_value}')
            if upload_metadata:
                response['Upload-Metadata'] = ','.join(upload_metadata)
            
            return response
            
        except Exception as e:
            logger.error(f"[TUS] 상태 확인 실패: {e}", exc_info=True)
            return HttpResponse(f'Internal Server Error: {str(e)}', status=500)
    
    def patch(self, request, upload_id: str):
        """
        TUS 청크 업로드 (PATCH)
        
        Headers:
        - Upload-Offset: 현재 업로드 오프셋 (필수)
        - Content-Type: application/offset+octet-stream
        
        Body:
        - 청크 데이터 (바이너리)
        
        Response:
        - 204 No Content (성공)
        - Upload-Offset: 업데이트된 오프셋
        """
        try:
            # Upload-Offset 헤더 확인
            upload_offset_header = request.META.get('HTTP_UPLOAD_OFFSET')
            if not upload_offset_header:
                return HttpResponse('Missing Upload-Offset header', status=400)
            
            try:
                expected_offset = int(upload_offset_header)
            except ValueError:
                return HttpResponse('Invalid Upload-Offset', status=400)
            
            # 메타데이터 로드
            metadata_file_path = TUS_METADATA_DIR / f'{upload_id}.json'
            upload_file_path = TUS_UPLOAD_DIR / f'{upload_id}.bin'
            
            if not metadata_file_path.exists():
                return HttpResponse('Upload not found', status=404)
            
            with open(metadata_file_path, 'r') as f:
                metadata_data = json.load(f)
            
            # 현재 파일 크기 확인
            if upload_file_path.exists():
                current_offset = upload_file_path.stat().st_size
            else:
                current_offset = 0
            
            # 오프셋 검증
            if expected_offset != current_offset:
                response = HttpResponse('Offset mismatch', status=409)
                response['Upload-Offset'] = str(current_offset)
                return response
            
            # 청크 데이터 읽기
            chunk_data = request.body
            if not chunk_data:
                return HttpResponse('No data in request body', status=400)
            
            # 파일에 청크 추가
            with open(upload_file_path, 'ab') as f:
                f.write(chunk_data)
            
            # 새로운 오프셋
            new_offset = current_offset + len(chunk_data)
            
            # 메타데이터 업데이트
            metadata_data['upload_offset'] = new_offset
            with open(metadata_file_path, 'w') as f:
                json.dump(metadata_data, f)
            
            # 응답
            response = HttpResponse(status=204)
            response['Upload-Offset'] = str(new_offset)
            response['Upload-Length'] = str(metadata_data['upload_length'])
            response['Tus-Resumable'] = '1.0.0'
            
            logger.debug(f"[TUS] 청크 업로드: upload_id={upload_id}, offset={new_offset}/{metadata_data['upload_length']}")
            
            return response
            
        except Exception as e:
            logger.error(f"[TUS] 청크 업로드 실패: {e}", exc_info=True)
            return HttpResponse(f'Internal Server Error: {str(e)}', status=500)
    
    def options(self, request, upload_id: Optional[str] = None):
        """CORS preflight 요청 처리"""
        response = HttpResponse(status=200)
        self._add_cors_headers(response, request)
        return response


@method_decorator(csrf_exempt, name='dispatch')
class TUSCompleteView(View):
    """
    TUS 업로드 완료 및 Cloudflare Stream 전송
    """
    
    def dispatch(self, request, *args, **kwargs):
        """인증 확인"""
        auth = AdminJWTAuthentication()
        try:
            user, token = auth.authenticate(request)
            if not user:
                return JsonResponse(create_error_response('Unauthorized', '01'), status=401)
            request.user = user
        except Exception as e:
            logger.error(f"TUS Complete 인증 실패: {e}")
            return JsonResponse(create_error_response('Unauthorized', '01'), status=401)
        
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, upload_id: str):
        """
        업로드 완료 및 Cloudflare Stream으로 전송
        
        Response:
        {
            "IndeAPIResponse": {
                "ErrorCode": "00",
                "Message": "비디오 업로드 성공",
                "Result": {
                    "videoStreamId": "...",
                    "embedUrl": "...",
                    ...
                }
            }
        }
        """
        try:
            metadata_file_path = TUS_METADATA_DIR / f'{upload_id}.json'
            upload_file_path = TUS_UPLOAD_DIR / f'{upload_id}.bin'
            
            if not metadata_file_path.exists() or not upload_file_path.exists():
                return JsonResponse(
                    create_error_response('Upload not found', '01'),
                    status=404
                )
            
            # 메타데이터 로드
            with open(metadata_file_path, 'r') as f:
                metadata_data = json.load(f)
            
            # 업로드 완료 확인
            file_size = upload_file_path.stat().st_size
            if file_size != metadata_data['upload_length']:
                return JsonResponse(
                    create_error_response(
                        f'Upload incomplete. Expected: {metadata_data["upload_length"]}, Got: {file_size}',
                        '01'
                    ),
                    status=400
                )
            
            logger.info(f"[TUS] 업로드 완료 확인: upload_id={upload_id}, size={file_size}")
            
            # Cloudflare Stream에 업로드
            cf_stream = get_cloudflare_stream()
            
            with open(upload_file_path, 'rb') as f:
                upload_result = cf_stream.upload_video(
                    file_obj=f,
                    filename=metadata_data['filename']
                )
            
            video_stream_id = upload_result['video_id']
            video_info = upload_result['video_info']
            
            # 응답 데이터 구성
            result = {
                'videoStreamId': video_stream_id,
                'embedUrl': cf_stream.get_video_embed_url(video_stream_id),
                'thumbnailUrl': cf_stream.get_video_thumbnail_url(video_stream_id),
                'hlsUrl': cf_stream.get_video_hls_url(video_stream_id),
                'dashUrl': cf_stream.get_video_dash_url(video_stream_id),
                'videoInfo': {
                    'status': video_info.get('status'),
                    'duration': video_info.get('duration'),
                    'size': video_info.get('size'),
                    'width': video_info.get('width'),
                    'height': video_info.get('height'),
                }
            }
            
            # 임시 파일 삭제
            try:
                upload_file_path.unlink()
                metadata_file_path.unlink()
            except Exception as e:
                logger.warning(f"[TUS] 임시 파일 삭제 실패: {e}")
            
            logger.info(f"[TUS] Cloudflare Stream 업로드 완료: upload_id={upload_id}, videoStreamId={video_stream_id}")
            
            return JsonResponse(
                create_success_response(result, '비디오 업로드 성공'),
                status=200
            )
            
        except Exception as e:
            logger.error(f"[TUS] 업로드 완료 처리 실패: {e}", exc_info=True)
            return JsonResponse(
                create_error_response(f'비디오 업로드 실패: {str(e)}', '99'),
                status=500
            )

