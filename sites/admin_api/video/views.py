"""
비디오/세미나 API 뷰
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import datetime
import logging

from sites.admin_api.video.models import Video
from sites.admin_api.video.serializers import (
    VideoSerializer,
    VideoListSerializer,
    VideoCreateSerializer,
    VideoUpdateSerializer,
)
from sites.admin_api.video.utils import (
    upload_thumbnail_to_s3,
    delete_video_images,
    get_presigned_thumbnail_url,
)
from sites.admin_api.authentication import AdminJWTAuthentication
from core.utils import create_success_response, create_error_response
from core.s3_storage import S3Storage, get_s3_storage
from core.cloudflare_stream import get_cloudflare_stream
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


class VideoListView(APIView):
    """
    비디오/세미나 목록 조회 API
    GET /video/list
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        비디오/세미나 목록 조회 (페이지네이션, 필터링, 검색 지원)
        
        Query Parameters:
        - page: 페이지 번호 (기본값: 1)
        - pageSize: 페이지 크기 (기본값: 20)
        - startDate: 시작 날짜 (YYYY-MM-DD)
        - endDate: 종료 날짜 (YYYY-MM-DD)
        - contentType: 콘텐츠 타입 (video, seminar)
        - category: 카테고리 (sysCodeSid)
        - visibility: 공개 범위 (sysCodeSid)
        - status: 상태 (sysCodeSid, 'deleted' 포함)
        - search: 검색어 (제목, 출연자, 키워드)
        - searchType: 검색 타입 (title, speaker, keyword)
        - editor: 작성자 (에디터명)
        - director: 작성자 (디렉터명)
        - sort: 정렬 (createdAt, viewCount, rating, shareCount)
        """
        try:
            # 쿼리 파라미터 파싱
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('pageSize', 20))
            start_date = request.query_params.get('startDate')
            end_date = request.query_params.get('endDate')
            content_type = request.query_params.get('contentType')
            category = request.query_params.get('category')
            visibility = request.query_params.get('visibility')
            status_filter = request.query_params.get('status')
            search = request.query_params.get('search')
            search_type = request.query_params.get('searchType', 'all')  # all, title, speaker, keyword
            editor = request.query_params.get('editor')
            director = request.query_params.get('director')
            sort = request.query_params.get('sort', 'createdAt')  # createdAt, viewCount, rating
            
            # 기본 쿼리셋
            # status가 'deleted'인 경우 삭제된 항목만 조회, 그 외에는 삭제되지 않은 항목만 조회
            if status_filter == 'deleted':
                queryset = Video.objects.filter(deletedAt__isnull=False)
            else:
                queryset = Video.objects.filter(deletedAt__isnull=True)
            
            # 날짜 필터링
            if start_date:
                try:
                    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                    queryset = queryset.filter(createdAt__gte=start_datetime)
                except ValueError:
                    pass
            
            if end_date:
                try:
                    end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                    end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                    queryset = queryset.filter(createdAt__lte=end_datetime)
                except ValueError:
                    pass
            
            # 콘텐츠 타입 필터링
            if content_type:
                queryset = queryset.filter(contentType=content_type)
            
            # 카테고리 필터링
            if category:
                queryset = queryset.filter(category=category)
            
            # 공개 범위 필터링
            if visibility:
                queryset = queryset.filter(visibility=visibility)
            
            # 상태 필터링
            if status_filter and status_filter != 'deleted':
                queryset = queryset.filter(status=status_filter)
            elif status_filter == 'deleted':
                queryset = queryset.filter(status='deleted')
            
            # 작성자 필터링
            if editor:
                queryset = queryset.filter(editor__icontains=editor)
            if director:
                queryset = queryset.filter(director__icontains=director)
            
            # 검색 (제목, 출연자, 키워드)
            if search:
                if search_type == 'title':
                    queryset = queryset.filter(
                        Q(title__icontains=search) |
                        Q(subtitle__icontains=search)
                    )
                elif search_type == 'speaker':
                    queryset = queryset.filter(
                        Q(speaker__icontains=search) |
                        Q(speakerAffiliation__icontains=search)
                    )
                elif search_type == 'keyword':
                    queryset = queryset.filter(tags__icontains=search)
                else:  # all
                    queryset = queryset.filter(
                        Q(title__icontains=search) |
                        Q(subtitle__icontains=search) |
                        Q(speaker__icontains=search) |
                        Q(speakerAffiliation__icontains=search) |
                        Q(tags__icontains=search)
                    )
            
            # 정렬
            if sort == 'viewCount':
                queryset = queryset.order_by('-viewCount', '-createdAt')
            elif sort == 'rating':
                queryset = queryset.order_by('-rating', '-createdAt')
            elif sort == 'shareCount':
                # shareCount는 현재 모델에 없으므로 createdAt으로 대체
                queryset = queryset.order_by('-createdAt')
            else:  # createdAt (기본값)
                queryset = queryset.order_by('-createdAt')
            
            # 페이지네이션
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            
            # 시리얼라이저
            serializer = VideoListSerializer(page_obj.object_list, many=True)
            videos_data = serializer.data
            
            # 각 비디오의 썸네일을 Presigned URL로 변환
            for video_data in videos_data:
                if video_data.get('thumbnail'):
                    video_data['thumbnail'] = get_presigned_thumbnail_url(
                        video_data['thumbnail'], 
                        expires_in=3600
                    )
            
            # 응답 데이터 구성
            result = {
                'videos': videos_data,
                'total': paginator.count,
                'page': page,
                'pageSize': page_size,
            }
            
            return Response(
                create_success_response(result, '비디오/세미나 목록 조회 성공'),
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"비디오 목록 조회 실패: {e}", exc_info=True)
            return Response(
                create_error_response(f'비디오/세미나 목록 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VideoDetailView(APIView):
    """
    비디오/세미나 상세 조회/수정/삭제 API
    GET /video/{id} - 상세 조회
    PUT /video/{id} - 수정
    DELETE /video/{id} - 삭제
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        """
        비디오/세미나 상세 조회
        """
        try:
            video = Video.objects.get(id=id, deletedAt__isnull=True)
            serializer = VideoSerializer(video)
            data = serializer.data.copy()
            
            # Cloudflare Stream 비디오 정보 추가
            if video.videoStreamId:
                try:
                    cf_stream = get_cloudflare_stream()
                    video_info = cf_stream.get_video(video.videoStreamId)
                    data['videoStreamInfo'] = {
                        'embedUrl': cf_stream.get_video_embed_url(video.videoStreamId),
                        'thumbnailUrl': cf_stream.get_video_thumbnail_url(video.videoStreamId),
                        'hlsUrl': cf_stream.get_video_hls_url(video.videoStreamId),
                        'dashUrl': cf_stream.get_video_dash_url(video.videoStreamId),
                        'status': video_info.get('status'),
                        'duration': video_info.get('duration'),
                        'size': video_info.get('size'),
                        'width': video_info.get('width'),
                        'height': video_info.get('height'),
                    }
                except Exception as e:
                    logger.warning(f"Cloudflare Stream 비디오 정보 조회 실패: {e}")
                    data['videoStreamInfo'] = None
            
            # 썸네일 URL을 Presigned URL로 변환
            if data.get('thumbnail'):
                data['thumbnail'] = get_presigned_thumbnail_url(data['thumbnail'], expires_in=3600)
            
            return Response(
                create_success_response(data, '비디오/세미나 조회 성공'),
                status=status.HTTP_200_OK
            )
            
        except Video.DoesNotExist:
            return Response(
                create_error_response('비디오/세미나를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"비디오 조회 실패: {e}", exc_info=True)
            return Response(
                create_error_response(f'비디오/세미나 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, id):
        """
        비디오/세미나 수정
        """
        try:
            video = Video.objects.get(id=id, deletedAt__isnull=True)
            
            # request.data에서 id 제거
            update_data = request.data.copy()
            if 'id' in update_data:
                del update_data['id']
            
            # 기존 Cloudflare Stream 비디오 ID 저장 (삭제용)
            old_video_stream_id = video.videoStreamId
            
            # 기존 Cloudflare Stream 비디오 ID 저장 (삭제용)
            old_video_stream_id = video.videoStreamId
            
            # 기존 썸네일 키 추출
            old_thumbnail = video.thumbnail
            old_thumbnail_key = None
            if old_thumbnail:
                old_thumbnail_key = S3Storage.extract_key_from_url(old_thumbnail)
            
            # 썸네일 처리: base64 데이터는 나중에 S3 업로드 후 저장
            thumbnail_from_request = request.data.get('thumbnail')
            
            if 'thumbnail' in request.data:
                if thumbnail_from_request and thumbnail_from_request.startswith('data:image'):
                    update_data['thumbnail'] = old_thumbnail if old_thumbnail else None
                elif thumbnail_from_request == '' or thumbnail_from_request is None:
                    update_data['thumbnail'] = None
            
            serializer = VideoUpdateSerializer(video, data=update_data, partial=True)
            
            if not serializer.is_valid():
                error_message = '입력값이 올바르지 않습니다.'
                if serializer.errors:
                    error_details = []
                    for field, errors in serializer.errors.items():
                        if isinstance(errors, list):
                            error_details.append(f"{field}: {', '.join(str(e) for e in errors)}")
                        else:
                            error_details.append(f"{field}: {str(errors)}")
                    if error_details:
                        error_message = '; '.join(error_details)
                
                return Response(
                    create_error_response(error_message, '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 시리얼라이저로 저장
            serializer.save()
            
            # videoStreamId가 변경된 경우 기존 비디오 삭제
            if 'videoStreamId' in update_data and update_data.get('videoStreamId') != old_video_stream_id:
                if old_video_stream_id:
                    try:
                        cf_stream = get_cloudflare_stream()
                        cf_stream.delete_video(old_video_stream_id)
                        logger.info(f"기존 Cloudflare Stream 비디오 삭제: {old_video_stream_id}")
                    except Exception as e:
                        logger.warning(f"기존 Cloudflare Stream 비디오 삭제 실패 (무시): {e}")
            
            # 썸네일을 S3에 업로드 (변경된 경우에만)
            if 'thumbnail' in request.data:
                original_thumbnail = request.data.get('thumbnail')
                
                if original_thumbnail is None or original_thumbnail == '':
                    # 썸네일 삭제
                    if old_thumbnail_key:
                        s3_storage = get_s3_storage()
                        s3_storage.delete_file(old_thumbnail_key)
                    video.thumbnail = None
                    video.save(update_fields=['thumbnail'])
                else:
                    if original_thumbnail.startswith('data:image'):
                        # base64 데이터인 경우 S3에 업로드
                        new_thumbnail_url = upload_thumbnail_to_s3(original_thumbnail, video.id)
                        if new_thumbnail_url:
                            video.thumbnail = new_thumbnail_url
                            video.save(update_fields=['thumbnail'])
                            
                            # 기존 썸네일 삭제 (새 썸네일과 키가 다른 경우)
                            new_thumbnail_key = S3Storage.extract_key_from_url(new_thumbnail_url)
                            if old_thumbnail_key and old_thumbnail_key != new_thumbnail_key:
                                s3_storage = get_s3_storage()
                                s3_storage.delete_file(old_thumbnail_key)
                    elif original_thumbnail != old_thumbnail:
                        # URL이 변경된 경우
                        video.thumbnail = original_thumbnail
                        video.save(update_fields=['thumbnail'])
            
            # 응답 데이터 생성
            serializer = VideoSerializer(video)
            data = serializer.data.copy()
            
            # 썸네일 URL을 Presigned URL로 변환
            if data.get('thumbnail'):
                data['thumbnail'] = get_presigned_thumbnail_url(data['thumbnail'], expires_in=3600)
            
            return Response(
                create_success_response(data, '비디오/세미나 수정 성공'),
                status=status.HTTP_200_OK
            )
            
        except Video.DoesNotExist:
            return Response(
                create_error_response('비디오/세미나를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"비디오 수정 실패: {e}", exc_info=True)
            return Response(
                create_error_response(f'비디오/세미나 수정 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, id):
        """
        비디오/세미나 삭제 (소프트 삭제)
        """
        try:
            video = Video.objects.get(id=id, deletedAt__isnull=True)
            
            # 삭제자 정보
            deleted_by = None
            if hasattr(request.user, 'memberShipSid'):
                deleted_by = request.user.memberShipSid
            elif hasattr(request.user, 'id'):
                deleted_by = str(request.user.id)
            
            # 소프트 삭제
            video.soft_delete(deleted_by=deleted_by)
            
            return Response(
                create_success_response(None, '비디오/세미나가 삭제되었습니다.'),
                status=status.HTTP_200_OK
            )
            
        except Video.DoesNotExist:
            return Response(
                create_error_response('비디오/세미나를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"비디오 삭제 실패: {e}", exc_info=True)
            return Response(
                create_error_response(f'비디오/세미나 삭제 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VideoCreateView(APIView):
    """
    비디오/세미나 생성 API
    POST /video/create
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        비디오/세미나 생성
        """
        try:
            serializer = VideoCreateSerializer(data=request.data)
            
            if not serializer.is_valid():
                error_message = '입력값이 올바르지 않습니다.'
                if serializer.errors:
                    error_details = []
                    for field, errors in serializer.errors.items():
                        if isinstance(errors, list):
                            error_details.append(f"{field}: {', '.join(str(e) for e in errors)}")
                        else:
                            error_details.append(f"{field}: {str(errors)}")
                    if error_details:
                        error_message = '; '.join(error_details)
                
                return Response(
                    create_error_response(error_message, '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 비디오 생성 (임시로 ID 획득)
            video = serializer.save()
            
            # 썸네일이 base64인 경우 S3에 업로드
            thumbnail_data = request.data.get('thumbnail')
            if thumbnail_data and thumbnail_data.startswith('data:image'):
                thumbnail_url = upload_thumbnail_to_s3(thumbnail_data, video.id)
                if thumbnail_url:
                    video.thumbnail = thumbnail_url
                    video.save(update_fields=['thumbnail'])
            
            # 응답 데이터 생성
            serializer = VideoSerializer(video)
            data = serializer.data.copy()
            
            # 썸네일 URL을 Presigned URL로 변환
            if data.get('thumbnail'):
                data['thumbnail'] = get_presigned_thumbnail_url(data['thumbnail'], expires_in=3600)
            
            return Response(
                create_success_response(data, '비디오/세미나 생성 성공'),
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"비디오 생성 실패: {e}", exc_info=True)
            return Response(
                create_error_response(f'비디오/세미나 생성 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VideoBatchDeleteView(APIView):
    """
    비디오/세미나 일괄 삭제 API
    DELETE /video/batch-delete
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        """
        비디오/세미나 일괄 삭제 (소프트 삭제)
        """
        try:
            ids = request.data.get('ids', [])
            
            if not ids or not isinstance(ids, list):
                return Response(
                    create_error_response('삭제할 비디오 ID 목록이 필요합니다.', '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 삭제자 정보
            deleted_by = None
            if hasattr(request.user, 'memberShipSid'):
                deleted_by = request.user.memberShipSid
            elif hasattr(request.user, 'id'):
                deleted_by = str(request.user.id)
            
            # 각 비디오에 대해 소프트 삭제
            deleted_count = 0
            for video_id in ids:
                try:
                    video = Video.objects.get(id=video_id, deletedAt__isnull=True)
                    video.soft_delete(deleted_by=deleted_by)
                    deleted_count += 1
                except Video.DoesNotExist:
                    continue
            
            return Response(
                create_success_response(
                    {'deleted_count': deleted_count},
                    f'{deleted_count}개의 비디오/세미나가 삭제되었습니다.'
                ),
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"비디오 일괄 삭제 실패: {e}", exc_info=True)
            return Response(
                create_error_response(f'비디오/세미나 일괄 삭제 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VideoBatchStatusView(APIView):
    """
    비디오/세미나 상태 일괄 변경 API
    PUT /video/batch-status
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        """
        비디오/세미나 상태 일괄 변경
        """
        try:
            ids = request.data.get('ids', [])
            new_status = request.data.get('status')
            
            if not ids or not isinstance(ids, list):
                return Response(
                    create_error_response('변경할 비디오 ID 목록이 필요합니다.', '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not new_status:
                return Response(
                    create_error_response('변경할 상태가 필요합니다.', '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 각 비디오의 상태 변경
            updated_count = 0
            for video_id in ids:
                try:
                    video = Video.objects.get(id=video_id, deletedAt__isnull=True)
                    video.status = new_status
                    video.save(update_fields=['status'])
                    updated_count += 1
                except Video.DoesNotExist:
                    continue
            
            return Response(
                create_success_response(
                    {'updated_count': updated_count},
                    f'{updated_count}개의 비디오/세미나 상태가 변경되었습니다.'
                ),
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"비디오 상태 일괄 변경 실패: {e}", exc_info=True)
            return Response(
                create_error_response(f'비디오/세미나 상태 일괄 변경 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VideoRestoreView(APIView):
    """
    비디오/세미나 복구 API
    POST /video/{id}/restore
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, id):
        """
        비디오/세미나 복구
        """
        try:
            video = Video.objects.get(id=id, deletedAt__isnull=False)
            video.restore()
            
            return Response(
                create_success_response(None, '비디오/세미나가 복구되었습니다.'),
                status=status.HTTP_200_OK
            )
            
        except Video.DoesNotExist:
            return Response(
                create_error_response('비디오/세미나를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"비디오 복구 실패: {e}", exc_info=True)
            return Response(
                create_error_response(f'비디오/세미나 복구 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VideoHardDeleteView(APIView):
    """
    비디오/세미나 영구 삭제 API
    DELETE /video/{id}/hard-delete
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, id):
        """
        비디오/세미나 영구 삭제
        """
        try:
            video = Video.objects.get(id=id)
            
            # Cloudflare Stream에서 비디오 삭제
            if video.videoStreamId:
                try:
                    cf_stream = get_cloudflare_stream()
                    cf_stream.delete_video(video.videoStreamId)
                    logger.info(f"Cloudflare Stream 비디오 삭제 성공: {video.videoStreamId}")
                except Exception as e:
                    logger.warning(f"Cloudflare Stream 비디오 삭제 실패 (무시): {e}")
            
            # 관련 이미지 삭제
            delete_video_images(video.id)
            
            # 데이터베이스에서 완전히 삭제
            video.delete()
            
            return Response(
                create_success_response(None, '비디오/세미나가 영구 삭제되었습니다.'),
                status=status.HTTP_200_OK
            )
            
        except Video.DoesNotExist:
            return Response(
                create_error_response('비디오/세미나를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"비디오 영구 삭제 실패: {e}", exc_info=True)
            return Response(
                create_error_response(f'비디오/세미나 영구 삭제 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VideoUploadView(APIView):
    """
    비디오 파일 업로드 API (Cloudflare Stream)
    POST /video/upload
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def post(self, request):
        """
        비디오 파일을 Cloudflare Stream에 업로드
        
        Request:
        - file: 업로드할 MP4 파일 (multipart/form-data)
        
        Response:
        {
            "IndeAPIResponse": {
                "ErrorCode": "00",
                "Message": "비디오 업로드 성공",
                "Result": {
                    "videoStreamId": "abc123...",
                    "embedUrl": "https://iframe.videodelivery.net/abc123...",
                    "thumbnailUrl": "https://videodelivery.net/abc123.../thumbnails/thumbnail.jpg",
                    "hlsUrl": "https://videodelivery.net/abc123.../manifest/video.m3u8"
                }
            }
        }
        """
        import time
        start_time = time.time()
        logger.info(f"[VideoUpload] 업로드 요청 수신 시작 - Content-Length: {request.META.get('CONTENT_LENGTH', 'Unknown')}")
        
        try:
            # 모든 파일은 서버 사이드 업로드로 처리
            if 'file' not in request.FILES:
                logger.warning("[VideoUpload] 파일이 요청에 없습니다.")
                return Response(
                    create_error_response('파일이 필요합니다.', '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )

            uploaded_file: UploadedFile = request.FILES['file']
            file_received_time = time.time()
            logger.info(f"[VideoUpload] 파일 수신 완료 - 파일명: {uploaded_file.name}, 크기: {uploaded_file.size} bytes, 수신 시간: {file_received_time - start_time:.2f}초")
            
            # 파일 확장자 확인
            if not uploaded_file.name.lower().endswith('.mp4'):
                return Response(
                    create_error_response('MP4 파일만 업로드 가능합니다.', '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 파일 크기 확인 (2GB 제한)
            MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
            file_size = uploaded_file.size
            if file_size > MAX_SIZE:
                return Response(
                    create_error_response(
                        f'파일 크기가 2GB를 초과합니다. (현재: {file_size / (1024*1024*1024):.2f}GB)',
                        '01'
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Cloudflare Stream에 업로드
            logger.info(f"[VideoUpload] Cloudflare Stream 업로드 시작 - 파일명: {uploaded_file.name}")
            cf_stream = get_cloudflare_stream()

            cf_upload_start = time.time()
            upload_result = cf_stream.upload_video(
                file_obj=uploaded_file.file,
                filename=uploaded_file.name
            )
            cf_upload_time = time.time() - cf_upload_start
            logger.info(f"[VideoUpload] Cloudflare Stream 업로드 완료 - 소요 시간: {cf_upload_time:.2f}초")
            
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
            
            total_time = time.time() - start_time
            logger.info(f"[VideoUpload] 전체 업로드 완료 - 총 소요 시간: {total_time:.2f}초, videoStreamId: {video_stream_id}")
            
            return Response(
                create_success_response(result, '비디오 업로드 성공'),
                status=status.HTTP_200_OK
            )
            
        except ValueError as e:
            return Response(
                create_error_response(str(e), '01'),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"비디오 업로드 실패: {e}", exc_info=True)
            return Response(
                create_error_response(f'비디오 업로드 실패: {str(e)}', '99'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VideoStreamInfoView(APIView):
    """
    Cloudflare Stream 비디오 정보 조회 API
    GET /video/stream/{videoStreamId}/info
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, videoStreamId):
        """
        Cloudflare Stream 비디오 정보 조회
        """
        try:
            cf_stream = get_cloudflare_stream()
            video_info = cf_stream.get_video(videoStreamId)
            
            result = {
                'videoStreamId': videoStreamId,
                'embedUrl': cf_stream.get_video_embed_url(videoStreamId),
                'thumbnailUrl': cf_stream.get_video_thumbnail_url(videoStreamId),
                'hlsUrl': cf_stream.get_video_hls_url(videoStreamId),
                'dashUrl': cf_stream.get_video_dash_url(videoStreamId),
                'videoInfo': video_info,
            }
            
            return Response(
                create_success_response(result, '비디오 정보 조회 성공'),
                status=status.HTTP_200_OK
            )
            
        except ValueError as e:
            return Response(
                create_error_response(str(e), '01'),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"비디오 정보 조회 실패: {e}", exc_info=True)
            return Response(
                create_error_response(f'비디오 정보 조회 실패: {str(e)}', '99'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

