"""
Public API JWT 인증 클래스
- 토큰: Authorization Bearer 또는 쿠키(accessToken)
- JWT의 user_id는 로그인 시 PublicMemberShip.member_sid로 채워짐.
- ArticleHighlight 등은 IndeUser FK를 사용하므로, member_sid → PublicMemberShip → 동일 email의 IndeUser로 조회.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from sites.public_api.models import IndeUser, PublicMemberShip
from sites.public_api.utils import get_token_from_request, verify_jwt_token


def _member_to_inde_user(member):
    """PublicMemberShip에 대응하는 IndeUser 반환 (없으면 동일 email로 get_or_create)."""
    phone = (member.phone or '').strip() or f"sync-{member.member_sid}"
    inde_user, _ = IndeUser.objects.get_or_create(
        email=member.email,
        defaults={
            'name': member.name or '',
            'phone': phone,
            'position': member.position or '',
            'joined_via': member.joined_via or 'LOCAL',
            'profile_completed': getattr(member, 'profile_completed', True),
            'is_active': True,
        },
    )
    return inde_user


class PublicJWTAuthentication(BaseAuthentication):
    """
    JWT 토큰 인증 클래스
    Authorization: Bearer 헤더 또는 쿠키(accessToken)에서 access_token 추출 후 사용자 인증.
    JWT user_id = PublicMemberShip.member_sid 이므로, PublicMemberShip 조회 후 동일 email의 IndeUser를 반환.
    """
    
    def authenticate(self, request):
        """
        Bearer 헤더 또는 쿠키에서 JWT 토큰을 검증하고 IndeUser를 반환
        
        Args:
            request: HTTP 요청 객체
        
        Returns:
            tuple: (IndeUser, token) 또는 None
        """
        access_token = get_token_from_request(request)
        
        if not access_token:
            return None
        
        payload = verify_jwt_token(access_token, token_type='access')
        if not payload:
            return None
        
        user_id = payload.get('user_id')
        if not user_id:
            return None
        
        try:
            member_sid = int(user_id)
        except (TypeError, ValueError):
            return None
        
        try:
            member = PublicMemberShip.objects.get(member_sid=member_sid, is_active=True)
        except PublicMemberShip.DoesNotExist:
            raise AuthenticationFailed('User not found')
        
        inde_user = _member_to_inde_user(member)
        if not inde_user.is_active:
            raise AuthenticationFailed('User not found')
        return (inde_user, access_token)




