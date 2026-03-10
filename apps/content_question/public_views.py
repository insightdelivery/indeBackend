"""
공개/사용자 API: 콘텐츠 질문 조회, 답변 등록
- GET /api/content/{content_type}/{content_id}/questions/  질문 목록
- POST /api/content/question-answer/  답변 등록
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny  # 또는 IsAuthenticated 로 로그인 필수 시 변경

from core.utils import create_success_response, create_error_response
from .models import ContentQuestion, ContentQuestionAnswer
from .serializers import ContentQuestionPublicSerializer, ContentQuestionAnswerCreateSerializer


class ContentQuestionListView(APIView):
    """GET /api/content/{content_type}/{content_id}/questions/"""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, content_type, content_id):
        if content_type not in ('ARTICLE', 'VIDEO', 'SEMINAR'):
            return Response(
                create_error_response('content_type은 ARTICLE, VIDEO, SEMINAR 중 하나여야 합니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = ContentQuestion.objects.filter(
            content_type=content_type,
            content_id=content_id,
        ).order_by('sort_order', 'question_id')
        serializer = ContentQuestionPublicSerializer(qs, many=True)
        return Response(create_success_response(serializer.data, '조회 성공'))


class ContentQuestionAnswerCreateView(APIView):
    """POST /api/content/question-answer/  답변 등록"""
    # 로그인 필수 시: authentication_classes = [JWT 등], permission_classes = [IsAuthenticated]
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ContentQuestionAnswerCreateSerializer(data=request.data)
        if not serializer.is_valid():
            msg = '; '.join(
                f'{k}: {", ".join(str(e) for e in v)}'
                for k, v in serializer.errors.items()
            )
            return Response(
                create_error_response(msg or '입력값이 올바르지 않습니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = serializer.validated_data
        question_id = data['question_id']
        content_type = data['content_type']
        content_id = data['content_id']
        answer_text = data['answer_text']

        try:
            question = ContentQuestion.objects.get(question_id=question_id)
        except ContentQuestion.DoesNotExist:
            return Response(
                create_error_response('질문을 찾을 수 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
            )
        if question.content_type != content_type or question.content_id != content_id:
            return Response(
                create_error_response('질문이 해당 콘텐츠와 일치하지 않습니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        # 사용자 ID: request.user(인증 미들웨어) 또는 요청 body의 user_id. 실제 서비스에서는 JWT 등으로 user_id 확정 권장
        user_id = None
        if hasattr(request, 'user') and request.user and getattr(request.user, 'is_authenticated', False):
            user_id = getattr(request.user, 'id', None) or getattr(request.user, 'user_id', None)
        if user_id is None:
            user_id = request.data.get('user_id')
        if user_id is None:
            return Response(
                create_error_response('로그인이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return Response(
                create_error_response('user_id가 올바르지 않습니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )

        if ContentQuestionAnswer.objects.filter(question_id=question_id, user_id=user_id).exists():
            return Response(
                create_error_response('이미 해당 질문에 답변하셨습니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )

        answer = ContentQuestionAnswer.objects.create(
            question=question,
            content_type=content_type,
            content_id=content_id,
            user_id=user_id,
            answer_text=answer_text,
        )
        # 첫 답변 등록 시 질문 잠금 (수정 불가 표시)
        if not question.is_locked:
            ContentQuestion.objects.filter(question_id=question_id).update(is_locked=True)

        return Response(
            create_success_response(
                {'answer_id': answer.answer_id, 'question_id': question_id},
                '답변이 등록되었습니다.',
            ),
            status=status.HTTP_201_CREATED,
        )
