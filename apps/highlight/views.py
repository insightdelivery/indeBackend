"""
Article Highlight API (articleHightlightPlan.md §5, 15.5)
- 인증: PublicJWTAuthentication, 로그인 사용자만 허용
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from sites.public_api.authentication import PublicJWTAuthentication
from core.utils import create_success_response, create_error_response
from .models import ArticleHighlight
from .serializers import ArticleHighlightSerializer, ArticleHighlightCreateSerializer
from . import services


class HighlightListCreateView(APIView):
    """GET /api/highlights?articleId={id} - 목록 | POST /api/highlights - 생성"""
    authentication_classes = [PublicJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """목록 조회"""
        if not request.user:
            return Response(
                create_error_response('로그인이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        article_id = request.query_params.get('articleId')
        if not article_id:
            return Response(
                create_error_response('articleId 쿼리가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            aid = int(article_id)
        except (TypeError, ValueError):
            return Response(
                create_error_response('articleId는 숫자여야 합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = ArticleHighlight.objects.filter(article_id=aid, user=request.user).order_by('paragraph_index', 'start_offset')
        serializer = ArticleHighlightSerializer(qs, many=True)
        return Response(
            create_success_response(serializer.data, '목록 조회 성공'),
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        """생성 (단일 또는 배열) - HighlightCreateView 로직과 동일"""
        if not request.user:
            return Response(
                create_error_response('로그인이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        data = request.data
        if data is None:
            return Response(
                create_error_response('요청 본문이 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(data, dict):
            payload_list = [data]
        elif isinstance(data, list):
            payload_list = data
        else:
            return Response(
                create_error_response('articleId, paragraphIndex, highlightText, startOffset, endOffset 등이 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ArticleHighlightCreateSerializer(data=payload_list, many=True)
        if not serializer.is_valid():
            return Response(
                create_error_response(serializer.errors or '검증 실패'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        validated = serializer.validated_data
        try:
            created_list, group_id = services.create_highlights(request.user, validated)
        except ValueError as e:
            return Response(
                create_error_response(str(e)),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not created_list:
            return Response(
                create_error_response('articleId가 없거나 Article이 존재하지 않습니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(created_list) == 1:
            return Response(
                create_success_response({'highlightId': created_list[0].id}, '생성됨'),
                status=status.HTTP_201_CREATED,
            )
        return Response(
            create_success_response({
                'highlightGroupId': group_id,
                'highlightIds': [h.id for h in created_list],
            }, '생성됨'),
            status=status.HTTP_201_CREATED,
        )


class HighlightDeleteView(APIView):
    """DELETE /api/highlights/{highlightId} - 단건 삭제 (본인만)"""
    authentication_classes = [PublicJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, highlight_id):
        if not request.user:
            return Response(
                create_error_response('로그인이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            obj = ArticleHighlight.objects.get(id=highlight_id)
        except ArticleHighlight.DoesNotExist:
            return Response(
                create_error_response('해당 하이라이트를 찾을 수 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
            )
        if obj.user_id != request.user.id:
            return Response(
                create_error_response('본인 하이라이트만 삭제할 수 있습니다.', '03'),
                status=status.HTTP_403_FORBIDDEN,
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HighlightGroupDeleteView(APIView):
    """DELETE /api/highlights/group/{highlightGroupId} - 그룹 전체 삭제 (본인만)"""
    authentication_classes = [PublicJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, highlight_group_id):
        if not request.user:
            return Response(
                create_error_response('로그인이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        qs = ArticleHighlight.objects.filter(highlight_group_id=highlight_group_id, user=request.user)
        count = qs.count()
        if count == 0:
            return Response(
                create_error_response('해당 그룹을 찾을 수 없거나 권한이 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
            )
        qs.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
