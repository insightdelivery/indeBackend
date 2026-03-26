"""
회원 short 공유 링크 API — contentShareLinkCopy.md
"""
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.utils import create_success_response, create_error_response
from sites.public_api.library_useractivity_views import _get_member
from sites.public_api.content_share_service import (
    ensure_share_link,
    resolve_short_code,
    get_row_for_visit_by_short_code,
    get_short_code_for_copy_entitlement,
)

CONTENT_TYPES = {'ARTICLE', 'VIDEO', 'SEMINAR'}

COOKIE_NAME = 'share_access'


def _share_cookie_flags(request):
    """로컬 HTTP: Secure=False. 운영 HTTPS: Secure=True."""
    secure = not getattr(settings, 'DEBUG', True)
    if request.is_secure():
        secure = True
    return secure


class LibraryContentShareEnsure(APIView):
    """POST /api/library/content-share/ensure — 로그인 회원만. §5.3 발급·갱신."""

    permission_classes = []

    def post(self, request):
        member = _get_member(request)
        if not member:
            return Response(
                create_error_response('인증이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        data = request.data or {}
        content_type = (data.get('contentType') or '').strip().upper()
        content_code = data.get('contentCode')
        try:
            content_id = int(content_code)
        except (TypeError, ValueError):
            content_id = None
        if content_type not in CONTENT_TYPES or not content_id or content_id < 1:
            return Response(
                create_error_response('contentType, contentCode(양의 정수)가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = ensure_share_link(member.pk, content_type, content_id)
        except RuntimeError as e:
            return Response(
                create_error_response(str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        exp = result['expired_at']
        expired_iso = exp.isoformat() if hasattr(exp, 'isoformat') else str(exp)
        return Response(
            create_success_response(
                {
                    'mode': result['mode'],
                    'shortCode': result['short_code'],
                    'expiredAt': expired_iso,
                }
            ),
            status=status.HTTP_200_OK,
        )


class LibraryContentShareResolve(APIView):
    """GET /api/library/content-share/resolve?shortCode= — short → 콘텐츠 (공개)."""

    permission_classes = []

    def get(self, request):
        short_code = (request.query_params.get('shortCode') or '').strip()
        if not short_code:
            return Response(
                create_error_response('shortCode가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        row = resolve_short_code(short_code)
        if not row:
            return Response(
                create_error_response('링크를 찾을 수 없습니다.'),
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            create_success_response(
                {
                    'contentType': row['content_type'],
                    'contentId': row['content_id'],
                    'expired': row['expired'],
                }
            ),
            status=status.HTTP_200_OK,
        )


class LibraryContentShareVisit(APIView):
    """
    GET /api/library/content-share/visit?shortCode=
    유효 시 share_access=share_token HttpOnly 쿠키 설정(§10.4·§10.15.5).
    """

    permission_classes = []

    def get(self, request):
        short_code = (request.query_params.get('shortCode') or '').strip()
        if not short_code:
            return Response(
                create_error_response('shortCode가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        row = get_row_for_visit_by_short_code(short_code)
        if not row:
            return Response(
                create_error_response('링크를 찾을 수 없습니다.'),
                status=status.HTTP_404_NOT_FOUND,
            )
        resp = Response(
            create_success_response(
                {
                    'contentType': row['content_type'],
                    'contentId': row['content_id'],
                    'expired': row['expired'],
                }
            ),
            status=status.HTTP_200_OK,
        )
        if not row['expired'] and row.get('share_token'):
            exp_at = row['expired_at']
            if timezone.is_naive(exp_at):
                exp_at = timezone.make_aware(exp_at, timezone.get_current_timezone())
            now = timezone.now()
            max_age = max(0, int((exp_at - now).total_seconds()))
            secure = _share_cookie_flags(request)
            resp.set_cookie(
                COOKIE_NAME,
                row['share_token'],
                max_age=max_age,
                httponly=True,
                secure=secure,
                samesite='Lax',
                path='/',
            )
        resp['Cache-Control'] = 'private, no-store'
        return resp


class LibraryContentShareForCopy(APIView):
    """
    GET /api/library/content-share/for-copy?contentType=&contentCode=
    share_access 쿠키 + DB 검증(§10.16.3) 후 short_code만 반환. 복사 URL 조립은 클라이언트(buildShortSharePageUrl).
    """

    permission_classes = []

    def get(self, request):
        content_type = (request.query_params.get('contentType') or '').strip().upper()
        try:
            content_id = int(request.query_params.get('contentCode') or 0)
        except (TypeError, ValueError):
            content_id = 0
        if content_type not in CONTENT_TYPES or content_id < 1:
            return Response(
                create_error_response('contentType, contentCode(양의 정수)가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        raw = request.COOKIES.get(COOKIE_NAME)
        if not raw:
            return Response(
                create_success_response({'eligible': False, 'reason': 'no_entitlement'}),
                status=status.HTTP_200_OK,
            )
        short_code = get_short_code_for_copy_entitlement(raw, content_type, content_id)
        if not short_code:
            return Response(
                create_success_response({'eligible': False, 'reason': 'invalid_or_expired'}),
                status=status.HTTP_200_OK,
            )
        resp = Response(
            create_success_response({'eligible': True, 'shortCode': short_code}),
            status=status.HTTP_200_OK,
        )
        resp['Cache-Control'] = 'private, no-store'
        return resp
