"""
공개/사용자 API: 콘텐츠 질문 조회, 답변 등록
- GET /api/content/{content_type}/{content_id}/questions/  질문 목록
- GET /api/content/{content_type}/{content_id}/my-answers/  로그인 사용자의 해당 콘텐츠 답변 목록
- POST /api/content/question-answer/  답변 등록
- PATCH /api/content/question-answer/{answer_id}/  답변 수정
- DELETE /api/content/question-answer/{answer_id}/  답변 삭제
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from core.utils import create_success_response, create_error_response
from sites.public_api.authentication import PublicJWTAuthentication
from sites.public_api.models import PublicMemberShip

from .models import ContentQuestion, ContentQuestionAnswer
from .serializers import (
    ContentQuestionPublicSerializer,
    ContentQuestionAnswerCreateSerializer,
    ContentQuestionAnswerUpdateSerializer,
)


def _get_member_sid(request):
    try:
        member = PublicMemberShip.objects.get(email=request.user.email, is_active=True)
        return member.member_sid
    except PublicMemberShip.DoesNotExist:
        return None


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
    """POST /api/content/question-answer/  답변 등록 (Authorization Bearer 또는 쿠키 accessToken)"""
    authentication_classes = [PublicJWTAuthentication]
    permission_classes = [IsAuthenticated]

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
        # JWT의 user_id는 member_sid; content_question_answer.user_id는 동일 정수 키 사용
        user_id = _get_member_sid(request)
        if user_id is None:
            return Response(
                create_error_response('회원 정보를 찾을 수 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
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


class ContentQuestionMyAnswersView(APIView):
    """GET /api/content/{content_type}/{content_id}/my-answers/ — 로그인 사용자의 답변만"""

    authentication_classes = [PublicJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, content_type, content_id):
        if content_type not in ('ARTICLE', 'VIDEO', 'SEMINAR'):
            return Response(
                create_error_response('content_type은 ARTICLE, VIDEO, SEMINAR 중 하나여야 합니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_id = _get_member_sid(request)
        if user_id is None:
            return Response(
                create_error_response('회원 정보를 찾을 수 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
            )
        qs = ContentQuestionAnswer.objects.filter(
            content_type=content_type,
            content_id=content_id,
            user_id=user_id,
        ).order_by('question_id')
        data = [
            {
                'answer_id': a.answer_id,
                'question_id': a.question_id,
                'answer_text': a.answer_text,
            }
            for a in qs
        ]
        return Response(create_success_response(data, '조회 성공'))


class ContentQuestionAnswerDetailView(APIView):
    """PATCH/DELETE /api/content/question-answer/{answer_id}/ — 본인 답변만"""

    authentication_classes = [PublicJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, answer_id):
        user_id = _get_member_sid(request)
        if user_id is None:
            return Response(
                create_error_response('회원 정보를 찾을 수 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            answer = ContentQuestionAnswer.objects.get(answer_id=answer_id)
        except ContentQuestionAnswer.DoesNotExist:
            return Response(
                create_error_response('답변을 찾을 수 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
            )
        if answer.user_id != user_id:
            return Response(
                create_error_response('권한이 없습니다.', '03'),
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ContentQuestionAnswerUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            msg = '; '.join(
                f'{k}: {", ".join(str(e) for e in v)}'
                for k, v in serializer.errors.items()
            )
            return Response(
                create_error_response(msg or '입력값이 올바르지 않습니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        answer.answer_text = serializer.validated_data['answer_text']
        answer.save(update_fields=['answer_text'])
        return Response(
            create_success_response(
                {'answer_id': answer.answer_id, 'question_id': answer.question_id},
                '답변이 수정되었습니다.',
            ),
            status=status.HTTP_200_OK,
        )

    def delete(self, request, answer_id):
        user_id = _get_member_sid(request)
        if user_id is None:
            return Response(
                create_error_response('회원 정보를 찾을 수 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            answer = ContentQuestionAnswer.objects.get(answer_id=answer_id)
        except ContentQuestionAnswer.DoesNotExist:
            return Response(
                create_error_response('답변을 찾을 수 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
            )
        if answer.user_id != user_id:
            return Response(
                create_error_response('권한이 없습니다.', '03'),
                status=status.HTTP_403_FORBIDDEN,
            )
        qid = answer.question_id
        answer.delete()
        return Response(
            create_success_response({'question_id': qid}, '답변이 삭제되었습니다.'),
            status=status.HTTP_200_OK,
        )
