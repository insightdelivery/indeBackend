"""
콘텐츠 저자(Content Author) API 뷰
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.paginator import Paginator

from .models import ContentAuthor, ContentAuthorContentType
from .serializers import (
    ContentAuthorListSerializer,
    ContentAuthorDetailSerializer,
    ContentAuthorCreateSerializer,
    ContentAuthorUpdateSerializer,
)
from sites.admin_api.authentication import AdminJWTAuthentication
from core.utils import create_success_response, create_error_response, create_api_response
from core.s3_storage import get_s3_storage, S3Storage

logger = logging.getLogger(__name__)


def _profile_image_to_presigned(url, expires_in=3600):
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


class AuthorListView(APIView):
    """저자 목록 조회 GET /authors/list/"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            queryset = ContentAuthor.objects.all().order_by('-created_at')
            name = request.query_params.get('name', '').strip()
            status_filter = request.query_params.get('status', '').strip()
            content_type = request.query_params.get('content_type', '').strip()
            if name:
                queryset = queryset.filter(name__icontains=name)
            if status_filter and status_filter in (ContentAuthor.STATUS_ACTIVE, ContentAuthor.STATUS_INACTIVE):
                queryset = queryset.filter(status=status_filter)
            if content_type and content_type in ('ARTICLE', 'VIDEO', 'SEMINAR'):
                queryset = queryset.filter(content_types__content_type=content_type).distinct()

            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('pageSize', 20)), 100)
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            serializer = ContentAuthorListSerializer(page_obj.object_list, many=True)
            authors_data = serializer.data
            for a in authors_data:
                if a.get('profile_image'):
                    a['profile_image'] = _profile_image_to_presigned(a['profile_image'])
            result = {
                'authors': authors_data,
                'total': paginator.count,
                'page': page,
                'pageSize': page_size,
            }
            return Response(
                create_success_response(result, '저자 목록 조회 성공'),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                create_error_response(f'저자 목록 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AuthorCreateView(APIView):
    """저자 등록 POST /authors/create/"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ContentAuthorCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                create_api_response(False, '01', '입력값이 올바르지 않습니다.', result={'errors': serializer.errors}),
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = serializer.validated_data.copy()
        content_types = data.pop('content_types', []) or []
        member_ship_sid = data.get('member_ship_sid')
        if member_ship_sid is not None and (isinstance(member_ship_sid, str) and not member_ship_sid.strip()):
            data['member_ship_sid'] = None
        author = ContentAuthor.objects.create(**data)
        for ct in content_types:
            ContentAuthorContentType.objects.get_or_create(author=author, content_type=ct)
        result = ContentAuthorDetailSerializer(author).data
        if result.get('profile_image'):
            result['profile_image'] = _profile_image_to_presigned(result['profile_image'])
        return Response(
            create_success_response(result, '저자 등록 성공'),
            status=status.HTTP_201_CREATED,
        )


class AuthorDetailView(APIView):
    """저자 상세 조회/수정/삭제 GET/PUT/DELETE /authors/{id}/"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            author = ContentAuthor.objects.get(author_id=id)
            serializer = ContentAuthorDetailSerializer(author)
            data = serializer.data.copy()
            if data.get('profile_image'):
                data['profile_image'] = _profile_image_to_presigned(data['profile_image'])
            return Response(
                create_success_response(data, '저자 조회 성공'),
                status=status.HTTP_200_OK,
            )
        except ContentAuthor.DoesNotExist:
            return Response(
                create_error_response('저자를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                create_error_response(f'저자 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, id):
        try:
            author = ContentAuthor.objects.get(author_id=id)
            serializer = ContentAuthorUpdateSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(
                    create_api_response(False, '01', '입력값이 올바르지 않습니다.', result={'errors': serializer.errors}),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            data = serializer.validated_data.copy()
            content_types = data.pop('content_types', None)
            member_ship_sid = data.get('member_ship_sid')
            if member_ship_sid is not None and (isinstance(member_ship_sid, str) and not member_ship_sid.strip()):
                data['member_ship_sid'] = None
            for key, value in data.items():
                setattr(author, key, value)
            author.save()
            if content_types is not None:
                author.content_types.exclude(content_type__in=content_types).delete()
                for ct in content_types:
                    ContentAuthorContentType.objects.get_or_create(author=author, content_type=ct)
            result = ContentAuthorDetailSerializer(author).data
            if result.get('profile_image'):
                result['profile_image'] = _profile_image_to_presigned(result['profile_image'])
            return Response(
                create_success_response(result, '저자 수정 성공'),
                status=status.HTTP_200_OK,
            )
        except ContentAuthor.DoesNotExist:
            return Response(
                create_error_response('저자를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                create_error_response(f'저자 수정 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, id):
        try:
            author = ContentAuthor.objects.get(author_id=id)
            author.delete()
            return Response(
                create_success_response({'author_id': id}, '저자 삭제 성공'),
                status=status.HTTP_200_OK,
            )
        except ContentAuthor.DoesNotExist:
            return Response(
                create_error_response('저자를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                create_error_response(f'저자 삭제 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AuthorsByContentTypeView(APIView):
    """콘텐츠 유형별 ACTIVE 저자 목록 GET /authors/by-content-type?type=ARTICLE|VIDEO|SEMINAR"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        content_type = request.query_params.get('type', '').strip().upper()
        if content_type not in ('ARTICLE', 'VIDEO', 'SEMINAR'):
            return Response(
                create_error_response('type 파라미터는 ARTICLE, VIDEO, SEMINAR 중 하나여야 합니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = ContentAuthor.objects.filter(
            status=ContentAuthor.STATUS_ACTIVE,
            content_types__content_type=content_type,
        ).distinct().order_by('name')
        serializer = ContentAuthorListSerializer(queryset, many=True)
        authors_data = serializer.data
        for a in authors_data:
            if a.get('profile_image'):
                a['profile_image'] = _profile_image_to_presigned(a['profile_image'])
        return Response(
            create_success_response({'authors': authors_data}, '저자 목록 조회 성공'),
            status=status.HTTP_200_OK,
        )
