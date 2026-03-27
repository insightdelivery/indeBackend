"""
GET /api/highlights/me/date | /api/highlights/me/article — 마이페이지 하이라이트 (wwwMypage_Highlights.md)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from sites.public_api.authentication import PublicJWTAuthentication
from core.utils import create_success_response, create_error_response

from . import mypage_service


class MyHighlightsByDateView(APIView):
    authentication_classes = [PublicJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user:
            return Response(
                create_error_response('로그인이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        data = mypage_service.build_date_view_result(request.user)
        return Response(create_success_response(data, '조회 성공'), status=status.HTTP_200_OK)


class MyHighlightsByArticleView(APIView):
    authentication_classes = [PublicJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user:
            return Response(
                create_error_response('로그인이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        data = mypage_service.build_article_view_result(request.user)
        return Response(create_success_response(data, '조회 성공'), status=status.HTTP_200_OK)
