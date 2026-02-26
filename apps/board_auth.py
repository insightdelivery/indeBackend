"""
공지/FAQ/문의 게시판용 JWT 인증 및 권한.
JWT에서 member_sid를 추출해 PublicMemberShip을 로드하고, DRF 권한(IsAuthenticated, IsAdminUser)에 맞는 request.user 객체를 반환합니다.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import BasePermission
from sites.public_api.utils import get_token_from_request, verify_jwt_token
from sites.public_api.models import PublicMemberShip


class RequestUser:
    """DRF request.user 호환 래퍼. IsAuthenticated / IsAdminUser에서 사용."""
    def __init__(self, member):
        self.member = member
        self.is_authenticated = True
        self.is_staff = getattr(member, 'is_staff', False)


class BoardJWTAuthentication(BaseAuthentication):
    """
    쿠키 또는 Authorization Bearer에서 JWT를 읽어 PublicMemberShip을 로드하고
    RequestUser(member)를 반환합니다.
    """
    def authenticate(self, request):
        token = get_token_from_request(request)
        if not token:
            raise AuthenticationFailed('토큰이 전달되지 않았습니다. 로그인 후 다시 시도하세요.')
        payload = verify_jwt_token(token, token_type='access')
        if not payload:
            raise AuthenticationFailed('유효하지 않거나 만료된 토큰입니다. 다시 로그인하세요.')
        user_id = payload.get('user_id')
        if not user_id:
            raise AuthenticationFailed('토큰 형식이 올바르지 않습니다.')
        try:
            member = PublicMemberShip.objects.get(
                member_sid=int(user_id), is_active=True
            )
            member.refresh_from_db()  # DB에서 최신 is_staff 등 반영
            return (RequestUser(member), token)
        except (PublicMemberShip.DoesNotExist, ValueError, TypeError):
            raise AuthenticationFailed('유효하지 않은 토큰이거나 회원 정보를 찾을 수 없습니다.')


class IsStaffOrReadOnly(BasePermission):
    """
    조회(list/retrieve)는 허용, 생성/수정/삭제는 is_staff=True만 허용.
    403 시 원인 메시지를 담아 반환.
    """
    def has_permission(self, request, view):
        action = getattr(view, 'action', None)
        if action in (None, 'list', 'retrieve'):
            return True
        if not request.user:
            raise PermissionDenied('로그인이 필요합니다.')
        if not getattr(request.user, 'is_authenticated', False):
            raise PermissionDenied('로그인이 필요합니다.')
        if not getattr(request.user, 'is_staff', False):
            raise PermissionDenied(
                '공지/FAQ 작성·수정·삭제는 관리자만 가능합니다. '
                '관리자 권한 부여: python manage.py grant_staff 이메일'
            )
        return True
