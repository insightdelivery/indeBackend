"""
Admin API JWT 인증 클래스
"""
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from core.models import Account
from api.models import AdminMemberShip


class AdminJWTAuthentication(BaseAuthentication):
    """
    JWT 토큰 기반 인증 클래스
    Authorization 헤더에서 Bearer 토큰을 추출하여 사용자 인증
    """
    
    def authenticate(self, request):
        """
        JWT 토큰을 검증하고 사용자를 반환
        
        Args:
            request: HTTP 요청 객체
        
        Returns:
            tuple: (user, token) 또는 None
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return None
        
        # Bearer 토큰 형식 확인
        if not auth_header.startswith('Bearer '):
            return None
        
        # 토큰 추출
        token = auth_header.split(' ')[1]
        
        try:
            # JWT 토큰 디코딩
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # 토큰 타입 확인 (access 토큰만 허용)
            if payload.get('token_type') != 'access':
                raise AuthenticationFailed('Invalid token type')
            
            # 사이트 확인
            if payload.get('site') != 'admin_api':
                raise AuthenticationFailed('Invalid site')
            
            # 사용자 조회
            user_id = payload.get('user_id')
            if not user_id:
                raise AuthenticationFailed('User ID not found in token')
            
            # AdminMemberShip 우선 조회 (관리자 회원)
            try:
                admin_member = AdminMemberShip.objects.get(memberShipSid=user_id, is_active=True)
                # AdminMemberShip 객체를 반환 (request.user로 접근 가능)
                return (admin_member, token)
            except AdminMemberShip.DoesNotExist:
                pass
            
            # Account 조회 (기존 관리자)
            try:
                user = Account.objects.get(id=user_id, is_active=True)
                # 관리자 권한 확인
                if not user.is_staff:
                    raise AuthenticationFailed('User is not staff')
                return (user, token)
            except Account.DoesNotExist:
                raise AuthenticationFailed('User not found')
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except Exception as e:
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')


