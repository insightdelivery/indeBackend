"""
공개 홈페이지 정적 문서 GET /api/homepage-docs/{doc_type}/ (wwwDocEtc.md §4.3, §4.6)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from core.utils import create_success_response, create_error_response
from sites.admin_api.articles.utils import convert_s3_urls_to_presigned
from sites.admin_api.homepage_doc.constants import HOMEPAGE_DOC_TYPES
from sites.admin_api.homepage_doc.models import HomepageDocInfo
from sites.admin_api.homepage_doc.serializers import HomepageDocReadSerializer

class PublicHomepageDocDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, doc_type):
        if doc_type not in HOMEPAGE_DOC_TYPES:
            return Response(
                create_error_response('문서를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            obj = HomepageDocInfo.objects.get(doc_type=doc_type)
        except HomepageDocInfo.DoesNotExist:
            return Response(
                create_error_response('문서를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        if not obj.is_published:
            return Response(
                create_error_response('문서를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )

        data = HomepageDocReadSerializer(obj).data
        if data.get('bodyHtml'):
            data['bodyHtml'] = convert_s3_urls_to_presigned(data['bodyHtml'], expires_in=3600)

        # 관리자 저장 직후 www에서 새로고침 시 구버전이 보이지 않도록 브라우저·중간 캐시 보관 최소화
        return Response(
            create_success_response(data, '홈페이지 문서 조회 성공'),
            status=status.HTTP_200_OK,
            headers={'Cache-Control': 'no-store, max-age=0'},
        )
