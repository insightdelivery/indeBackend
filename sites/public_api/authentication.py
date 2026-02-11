"""
Public API JWT 인증 클래스 (쿠키 기반)
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from sites.public_api.models import IndeUser
from sites.public_api.utils import get_token_from_cookie, verify_jwt_token


class PublicJWTAuthentication(BaseAuthentication):
    """
    쿠키 기반 JWT 토큰 인증 클래스
    HttpOnly 쿠키에서 access_token을 추출하여 사용자 인증
    """
    
    def authenticate(self, request):
        """
        쿠키에서 JWT 토큰을 검증하고 사용자를 반환
        
        Args:
            request: HTTP 요청 객체
        
        Returns:
            tuple: (user, token) 또는 None
        """
        # 쿠키에서 토큰 추출
        access_token, _ = get_token_from_cookie(request)
        
        if not access_token:
            return None
        
        # 토큰 검증
        payload = verify_jwt_token(access_token, token_type='access')
        
        if not payload:
            return None
        
        # 사용자 ID 추출
        user_id = payload.get('user_id')
        if not user_id:
            return None
        
        try:
            # 사용자 조회
            user = IndeUser.objects.get(id=user_id, is_active=True)
            return (user, access_token)
        except IndeUser.DoesNotExist:
            raise AuthenticationFailed('User not found')
        except Exception as e:
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')




