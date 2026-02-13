"""
파일 업로드/다운로드 API
AWS S3를 사용한 파일 관리
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.uploadedfile import InMemoryUploadedFile
from core.s3_storage import get_s3_storage
from core.utils import create_success_response, create_error_response
from sites.admin_api.authentication import AdminJWTAuthentication
from rest_framework.permissions import IsAuthenticated
import os
import uuid
from datetime import datetime
from io import BytesIO


class FileUploadView(APIView):
    """
    파일 업로드 API
    POST /admin-api/files/upload/
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        """
        파일을 S3에 업로드
        
        요청:
        - file: 업로드할 파일 (multipart/form-data)
        - folder: 저장할 폴더 경로 (선택, 기본: 'uploads/')
        - prefix: 파일명 접두사 (선택)
        
        응답:
        {
            "IndeAPIResponse": {
                "ErrorCode": "00",
                "Message": "파일 업로드 성공",
                "Result": {
                    "url": "https://bucket.s3.region.amazonaws.com/path/to/file.jpg",
                    "key": "uploads/2024/01/file.jpg",
                    "filename": "file.jpg"
                }
            }
        }
        """
        try:
            if 'file' not in request.FILES:
                return Response(
                    create_error_response('파일이 제공되지 않았습니다.', '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            uploaded_file: InMemoryUploadedFile = request.FILES['file']
            folder = request.data.get('folder', 'uploads/')
            prefix = request.data.get('prefix', '')
            
            # 폴더 경로 정리 (끝에 / 추가)
            if folder and not folder.endswith('/'):
                folder += '/'
            
            # 날짜별 폴더 추가 (선택)
            date_folder = datetime.now().strftime('%Y/%m/')
            full_folder = f"{folder}{date_folder}"
            
            # 파일명 생성
            original_filename = uploaded_file.name
            file_ext = os.path.splitext(original_filename)[1]
            
            # S3에 저장할 파일명: 년월일시분초 형식 (YYYYMMDDHHMMSS)
            timestamp_filename = datetime.now().strftime('%Y%m%d%H%M%S')
            if prefix:
                filename = f"{prefix}_{timestamp_filename}{file_ext}"
            else:
                filename = f"{timestamp_filename}{file_ext}"
            
            s3_key = f"{full_folder}{filename}"
            
            # 파일을 BytesIO로 변환
            file_content = uploaded_file.read()
            file_obj = BytesIO(file_content)
            
            # Content-Type 설정
            content_type = uploaded_file.content_type or 'application/octet-stream'
            
            # S3에 업로드
            s3_storage = get_s3_storage()
            url = s3_storage.upload_file(
                file_obj=file_obj,
                key=s3_key,
                content_type=content_type,
                metadata={
                    'original_filename': original_filename,  # s3_storage.upload_file에서 자동으로 base64 인코딩됨
                    'uploaded_by': str(request.user.id) if hasattr(request.user, 'id') else 'unknown'
                }
            )
            
            return Response(
                create_success_response({
                    'url': url,
                    'key': s3_key,
                    'filename': filename,
                    'original_filename': original_filename,
                    'size': len(file_content),
                    'content_type': content_type
                }, '파일 업로드 성공'),
                status=status.HTTP_200_OK
            )
            
        except ValueError as e:
            return Response(
                create_error_response(str(e), '01'),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                create_error_response(f'파일 업로드 실패: {str(e)}', '99'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FileDeleteView(APIView):
    """
    파일 삭제 API
    DELETE /admin-api/files/delete/
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        """
        S3에서 파일 삭제
        
        요청:
        - key: 삭제할 파일의 S3 키 (필수)
        또는
        - url: 파일의 전체 URL (key 추출 가능)
        
        응답:
        {
            "IndeAPIResponse": {
                "ErrorCode": "00",
                "Message": "파일 삭제 성공",
                "Result": {"message": "파일이 삭제되었습니다."}
            }
        }
        """
        try:
            key = request.data.get('key') or request.query_params.get('key')
            url = request.data.get('url') or request.query_params.get('url')
            
            if not key and not url:
                return Response(
                    create_error_response('파일 키 또는 URL이 제공되지 않았습니다.', '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # URL에서 키 추출
            if url and not key:
                from core.s3_storage import S3Storage
                key = S3Storage.extract_key_from_url(url)
                if not key:
                    return Response(
                        create_error_response('유효하지 않은 파일 URL입니다.', '01'),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # S3에서 파일 삭제
            s3_storage = get_s3_storage()
            success = s3_storage.delete_file(key)
            
            if success:
                return Response(
                    create_success_response({'message': '파일이 삭제되었습니다.'}, '파일 삭제 성공'),
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    create_error_response('파일 삭제에 실패했습니다.', '99'),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            return Response(
                create_error_response(f'파일 삭제 실패: {str(e)}', '99'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FileInfoView(APIView):
    """
    파일 정보 조회 API
    GET /admin-api/files/info/
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        파일 정보 조회
        
        쿼리 파라미터:
        - key: 파일의 S3 키 (필수)
        또는
        - url: 파일의 전체 URL (key 추출 가능)
        
        응답:
        {
            "IndeAPIResponse": {
                "ErrorCode": "00",
                "Message": "파일 정보 조회 성공",
                "Result": {
                    "key": "uploads/2024/01/file.jpg",
                    "url": "https://bucket.s3.region.amazonaws.com/...",
                    "size": 12345,
                    "content_type": "image/jpeg",
                    "last_modified": "2024-01-01T00:00:00Z",
                    "exists": true
                }
            }
        }
        """
        try:
            key = request.query_params.get('key')
            url = request.query_params.get('url')
            
            if not key and not url:
                return Response(
                    create_error_response('파일 키 또는 URL이 제공되지 않았습니다.', '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # URL에서 키 추출
            if url and not key:
                from core.s3_storage import S3Storage
                key = S3Storage.extract_key_from_url(url)
                if not key:
                    return Response(
                        create_error_response('유효하지 않은 파일 URL입니다.', '01'),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            s3_storage = get_s3_storage()
            
            # 파일 존재 여부 확인
            exists = s3_storage.file_exists(key)
            
            if not exists:
                return Response(
                    create_error_response('파일을 찾을 수 없습니다.', '01'),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 파일 정보 가져오기
            file_info = s3_storage.get_file_info(key)
            file_url = s3_storage.get_file_url(key)
            
            result = {
                'key': key,
                'url': file_url,
                'exists': True,
                **file_info
            }
            
            return Response(
                create_success_response(result, '파일 정보 조회 성공'),
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                create_error_response(f'파일 정보 조회 실패: {str(e)}', '99'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FileListView(APIView):
    """
    파일 목록 조회 API
    GET /admin-api/files/list/
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        특정 경로의 파일 목록 조회
        
        쿼리 파라미터:
        - prefix: 파일 경로 접두사 (선택, 기본: 'uploads/')
        - max_keys: 최대 반환 개수 (선택, 기본: 1000)
        
        응답:
        {
            "IndeAPIResponse": {
                "ErrorCode": "00",
                "Message": "파일 목록 조회 성공",
                "Result": {
                    "files": ["uploads/2024/01/file1.jpg", "uploads/2024/01/file2.jpg"],
                    "count": 2
                }
            }
        }
        """
        try:
            prefix = request.query_params.get('prefix', 'uploads/')
            max_keys = int(request.query_params.get('max_keys', 1000))
            
            s3_storage = get_s3_storage()
            files = s3_storage.list_files(prefix=prefix, max_keys=max_keys)
            
            return Response(
                create_success_response({
                    'files': files,
                    'count': len(files)
                }, '파일 목록 조회 성공'),
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                create_error_response(f'파일 목록 조회 실패: {str(e)}', '99'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

