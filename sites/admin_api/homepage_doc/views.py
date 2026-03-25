import logging
from django.db import IntegrityError, transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from sites.admin_api.authentication import AdminJWTAuthentication
from core.utils import create_success_response, create_error_response

from .constants import HOMEPAGE_DOC_TYPES, HOMEPAGE_DOC_TYPES_ORDERED
from .models import HomepageDocInfo
from .serializers import HomepageDocReadSerializer, HomepageDocPutSerializer
from .utils import replace_base64_images_in_homepage_html
from sites.admin_api.articles.utils import convert_s3_urls_to_presigned

logger = logging.getLogger(__name__)


def _read_payload(instance):
    data = dict(HomepageDocReadSerializer(instance).data)
    if data.get('bodyHtml'):
        data['bodyHtml'] = convert_s3_urls_to_presigned(data['bodyHtml'], expires_in=3600)
    return data


def _ordered_queryset():
    from django.db.models import Case, When, IntegerField

    ordering = Case(
        *[When(doc_type=dt, then=pos) for pos, dt in enumerate(HOMEPAGE_DOC_TYPES_ORDERED)],
        default=99,
        output_field=IntegerField(),
    )
    return HomepageDocInfo.objects.filter(doc_type__in=HOMEPAGE_DOC_TYPES).order_by(ordering)


class AdminHomepageDocListView(APIView):
    """GET /homepage-doc-info/ — 7건"""

    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            rows = list(_ordered_queryset())
            data = [_read_payload(r) for r in rows]
            return Response(
                create_success_response({'documents': data}, '홈페이지 문서 목록 조회 성공'),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception('homepage_doc list')
            return Response(
                create_error_response(f'목록 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminHomepageDocDetailView(APIView):
    """GET/PUT /homepage-doc-info/{doc_type}/"""

    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_type):
        if doc_type not in HOMEPAGE_DOC_TYPES:
            return Response(
                create_error_response('문서 유형을 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            obj = HomepageDocInfo.objects.get(doc_type=doc_type)
        except HomepageDocInfo.DoesNotExist:
            return Response(
                create_error_response('문서를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            create_success_response(_read_payload(obj), '홈페이지 문서 조회 성공'),
            status=status.HTTP_200_OK,
        )

    def put(self, request, doc_type):
        if doc_type not in HOMEPAGE_DOC_TYPES:
            return Response(
                create_error_response('문서 유형을 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )

        ser = HomepageDocPutSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                create_error_response('입력값이 올바르지 않습니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )

        body = ser.validated_data
        existing = HomepageDocInfo.objects.filter(doc_type=doc_type).first()

        if 'title' in body:
            title = body['title']
        else:
            title = existing.title if existing else None

        if 'bodyHtml' in body:
            body_html = body['bodyHtml'] or ''
        else:
            body_html = existing.body_html if existing else ''

        if 'isPublished' in body:
            is_published = body['isPublished']
        else:
            is_published = existing.is_published if existing else True

        body_html = replace_base64_images_in_homepage_html(body_html or '')

        try:
            # INSERT와 UPDATE를 분리한 atomic: IntegrityError 시 첫 블록만 롤됨 (§4.2.1)
            try:
                with transaction.atomic():
                    HomepageDocInfo.objects.create(
                        doc_type=doc_type,
                        title=title,
                        body_html=body_html,
                        is_published=is_published,
                    )
            except IntegrityError:
                with transaction.atomic():
                    obj = HomepageDocInfo.objects.get(doc_type=doc_type)
                    obj.title = title
                    obj.body_html = body_html
                    obj.is_published = is_published
                    obj.save()
            obj = HomepageDocInfo.objects.get(doc_type=doc_type)
        except Exception as e:
            logger.exception('homepage_doc put')
            return Response(
                create_error_response(f'저장 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            create_success_response(_read_payload(obj), '홈페이지 문서 저장 성공'),
            status=status.HTTP_200_OK,
        )

