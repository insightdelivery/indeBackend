"""
공개/사용자 API: 콘텐츠 질문 조회, 답변 등록
- GET /api/content/my-answered-contents/  마이페이지 — 답변한 콘텐츠 목록 (페이지네이션)
- GET /api/content/{content_type}/{content_id}/questions/  질문 목록
- GET /api/content/{content_type}/{content_id}/my-answers/  로그인 사용자의 해당 콘텐츠 답변 목록
- POST /api/content/question-answer/  답변 등록
- PATCH /api/content/question-answer/{answer_id}/  답변 수정
- DELETE /api/content/question-answer/{answer_id}/  답변 삭제
"""
from django.db.models import Count, Max, Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from core.models import SysCodeManager
from core.utils import create_success_response, create_error_response
from sites.admin_api.articles.models import Article
from sites.admin_api.articles.utils import get_presigned_thumbnail_url as article_presigned_thumbnail
from sites.admin_api.video.models import Video
from sites.admin_api.video.utils import get_presigned_thumbnail_url as video_presigned_thumbnail
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


def _presign_thumb_article(url):
    if not url:
        return None
    try:
        return article_presigned_thumbnail(url, expires_in=3600) or url
    except Exception:
        return url


def _presign_thumb_video(url):
    if not url:
        return None
    try:
        return video_presigned_thumbnail(url, expires_in=3600) or url
    except Exception:
        return url


def _content_url_for_www(content_type: str, content_id: int) -> str:
    """frontend_www 정적 라우트: detail?id= (userApplyQuestions.md / videoPlan §6.10)."""
    if content_type == 'ARTICLE':
        return f'/article/detail?id={content_id}'
    if content_type == 'VIDEO':
        return f'/video/detail?id={content_id}'
    if content_type == 'SEMINAR':
        return f'/seminar/detail?id={content_id}'
    return '#'


_CONTENT_TYPE_LABEL_KO = {
    'ARTICLE': '아티클',
    'VIDEO': '비디오',
    'SEMINAR': '세미나',
}


class ContentMyAnsweredContentsListView(APIView):
    """
    GET /api/content/my-answered-contents/
    로그인 사용자가 적용 질문에 답변한 콘텐츠 목록 (GROUP BY + DB LIMIT/OFFSET).
    """

    authentication_classes = [PublicJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = _get_member_sid(request)
        if user_id is None:
            return Response(
                create_error_response('회원 정보를 찾을 수 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            page = int(request.query_params.get('page', 1) or 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(
                request.query_params.get('page_size')
                or request.query_params.get('pageSize')
                or 9
            )
        except (TypeError, ValueError):
            page_size = 9
        page_size = min(max(1, page_size), 50)
        page = max(1, page)

        grouped = (
            ContentQuestionAnswer.objects.filter(user_id=user_id)
            .values('content_type', 'content_id')
            .annotate(
                answer_count=Count('answer_id'),
                last_answered_at=Max('created_at'),
            )
            .order_by('-last_answered_at')
        )
        total = grouped.count()
        total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1
        if total > 0 and page > total_pages:
            page = total_pages
        if total == 0:
            page = 1

        start = (page - 1) * page_size
        page_slice = list(grouped[start : start + page_size])

        article_ids = [r['content_id'] for r in page_slice if r['content_type'] == 'ARTICLE']
        video_ids = [r['content_id'] for r in page_slice if r['content_type'] == 'VIDEO']
        seminar_ids = [r['content_id'] for r in page_slice if r['content_type'] == 'SEMINAR']

        article_map = {}
        if article_ids:
            for a in Article.objects.filter(
                id__in=article_ids,
                deletedAt__isnull=True,
            ).filter(Q(status='SYS26209B021') | Q(status='published')).only(
                'id', 'title', 'subtitle', 'thumbnail', 'category'
            ):
                article_map[a.id] = a

        video_map = {}
        seminar_map = {}
        vid_set = set(video_ids) | set(seminar_ids)
        if vid_set:
            for v in Video.objects.filter(
                id__in=list(vid_set),
                deletedAt__isnull=True,
                status='public',
            ).only('id', 'title', 'subtitle', 'thumbnail', 'category', 'contentType'):
                if v.contentType == 'video':
                    video_map[v.id] = v
                elif v.contentType == 'seminar':
                    seminar_map[v.id] = v

        category_codes = set()
        for row in page_slice:
            ct = row['content_type']
            cid = row['content_id']
            if ct not in _CONTENT_TYPE_LABEL_KO:
                continue
            meta = None
            if ct == 'ARTICLE':
                meta = article_map.get(cid)
            elif ct == 'VIDEO':
                meta = video_map.get(cid)
            elif ct == 'SEMINAR':
                meta = seminar_map.get(cid)
            if meta is None:
                continue
            raw = (getattr(meta, 'category', None) or '').strip()
            if raw:
                category_codes.add(raw)

        category_name_by_code = {}
        if category_codes:
            for sc in SysCodeManager.objects.filter(
                sysCodeSid__in=list(category_codes),
                sysCodeUse='Y',
            ).only('sysCodeSid', 'sysCodeName'):
                name = (sc.sysCodeName or '').strip()
                if name:
                    category_name_by_code[sc.sysCodeSid] = name

        results = []
        for row in page_slice:
            ct = row['content_type']
            cid = row['content_id']
            if ct not in _CONTENT_TYPE_LABEL_KO:
                continue

            meta = None
            if ct == 'ARTICLE':
                meta = article_map.get(cid)
            elif ct == 'VIDEO':
                meta = video_map.get(cid)
            elif ct == 'SEMINAR':
                meta = seminar_map.get(cid)

            if meta is None:
                continue

            thumb_raw = getattr(meta, 'thumbnail', None) or None
            if ct == 'ARTICLE':
                thumb_out = _presign_thumb_article(thumb_raw)
            else:
                thumb_out = _presign_thumb_video(thumb_raw)

            cat_raw = (getattr(meta, 'category', None) or '').strip()
            cat_name = category_name_by_code.get(cat_raw) if cat_raw else None
            sub = (getattr(meta, 'subtitle', None) or '').strip()
            last_at = row['last_answered_at']
            last_iso = last_at.isoformat() if last_at else None

            results.append(
                {
                    'contentType': ct,
                    'contentTypeLabel': _CONTENT_TYPE_LABEL_KO[ct],
                    'contentId': cid,
                    'categoryName': cat_name,
                    'title': meta.title,
                    'subtitle': sub or None,
                    'thumbnailUrl': thumb_out,
                    'lastAnsweredAt': last_iso,
                    'answerCount': row['answer_count'],
                    'contentUrl': _content_url_for_www(ct, cid),
                }
            )

        return Response(
            create_success_response(
                {
                    'list': results,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                },
                '조회 성공',
            ),
            status=status.HTTP_200_OK,
        )


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
