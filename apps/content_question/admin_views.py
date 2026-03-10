"""
관리자 API: 콘텐츠 질문 CRUD
- POST /content/questions/  질문 등록
- PUT /content/questions/{question_id}/  질문 수정 (답변 있으면 400)
- DELETE /content/questions/{question_id}/  질문 삭제
- GET /content/questions/?content_type=ARTICLE&content_id=10  목록 조회
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.utils import create_success_response, create_error_response
from sites.admin_api.authentication import AdminJWTAuthentication
from .models import ContentQuestion, ContentQuestionAnswer
from .serializers import (
    ContentQuestionListSerializer,
    ContentQuestionCreateSerializer,
    ContentQuestionUpdateSerializer,
)


class AdminContentQuestionListView(APIView):
    """GET 목록, POST 등록"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        content_type = request.query_params.get('content_type')
        content_id = request.query_params.get('content_id')
        if not content_type or not content_id:
            return Response(
                create_error_response('content_type, content_id 쿼리 파라미터가 필요합니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if content_type not in ('ARTICLE', 'VIDEO', 'SEMINAR'):
            return Response(
                create_error_response('content_type은 ARTICLE, VIDEO, SEMINAR 중 하나여야 합니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            content_id = int(content_id)
        except (TypeError, ValueError):
            return Response(
                create_error_response('content_id는 숫자여야 합니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = ContentQuestion.objects.filter(
            content_type=content_type,
            content_id=content_id,
        ).order_by('sort_order', 'question_id')
        serializer = ContentQuestionListSerializer(qs, many=True)
        return Response(create_success_response(serializer.data, '조회 성공'))

    def post(self, request):
        serializer = ContentQuestionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            msg = '; '.join(
                f'{k}: {", ".join(str(e) for e in v)}'
                for k, v in serializer.errors.items()
            )
            return Response(
                create_error_response(msg or '입력값이 올바르지 않습니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        # created_by: 관리자 ID (request.user 등에서 추출 가능 시 설정)
        created_by = getattr(request.user, 'id', None) or getattr(request.user, 'admin_id', None)
        if created_by is not None:
            serializer.validated_data['created_by'] = created_by
        question = serializer.save()
        out = ContentQuestionListSerializer(question).data
        return Response(
            create_success_response(out, '질문이 등록되었습니다.'),
            status=status.HTTP_201_CREATED,
        )


class AdminContentQuestionDetailView(APIView):
    """PUT 수정, DELETE 삭제"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_question(self, question_id):
        try:
            return ContentQuestion.objects.get(question_id=question_id)
        except ContentQuestion.DoesNotExist:
            return None

    def put(self, request, question_id):
        question = self._get_question(question_id)
        if not question:
            return Response(
                create_error_response('질문을 찾을 수 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
            )
        answer_count = ContentQuestionAnswer.objects.filter(question_id=question_id).count()
        if answer_count >= 1:
            return Response(
                create_error_response('답변이 이미 등록된 질문은 수정할 수 없습니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ContentQuestionUpdateSerializer(question, data=request.data, partial=True)
        if not serializer.is_valid():
            msg = '; '.join(
                f'{k}: {", ".join(str(e) for e in v)}'
                for k, v in serializer.errors.items()
            )
            return Response(
                create_error_response(msg or '입력값이 올바르지 않습니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        out = ContentQuestionListSerializer(question).data
        return Response(create_success_response(out, '질문이 수정되었습니다.'))

    def delete(self, request, question_id):
        question = self._get_question(question_id)
        if not question:
            return Response(
                create_error_response('질문을 찾을 수 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
            )
        question.delete()
        return Response(create_success_response(None, '질문이 삭제되었습니다.'), status=status.HTTP_200_OK)
