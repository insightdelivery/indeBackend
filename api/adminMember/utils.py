"""
관리자 회원 API 유틸리티 함수
JWT 토큰 생성 등
"""
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from api.models import AdminMemberShip


def create_admin_member_jwt_tokens(user: AdminMemberShip):
    """
    관리자 회원용 JWT 토큰 생성
    토큰 발급 시간을 사용자 모델에 저장하여 로그아웃 후 토큰 무효화 추적
    
    Args:
        user: AdminMemberShip 모델 인스턴스
    
    Returns:
        dict: access_token과 refresh_token을 포함한 딕셔너리
    """
    now = datetime.utcnow()
    access_expiration = now + timedelta(seconds=settings.JWT_ACCESS_EXPIRATION_DELTA)
    refresh_expiration = now + timedelta(seconds=settings.JWT_REFRESH_EXPIRATION_DELTA)
    
    # 토큰 발급 시간을 사용자 모델에 저장 (로그아웃 후 토큰 무효화 추적용)
    user.token_issued_at = timezone.now()
    user.save(update_fields=['token_issued_at'])
    
    # Access Token 페이로드
    access_payload = {
        'user_id': str(user.memberShipSid),  # memberShipSid 사용
        'username': user.memberShipId,
        'email': user.memberShipEmail,
        'name': user.memberShipName,
        'level': user.memberShipLevel,
        'is_admin': user.is_admin,
        'exp': access_expiration,
        'iat': now,
        'site': 'admin_api',
        'token_type': 'access',
    }
    
    # Refresh Token 페이로드
    refresh_payload = {
        'user_id': str(user.memberShipSid),  # memberShipSid 사용
        'username': user.memberShipId,
        'exp': refresh_expiration,
        'iat': now,
        'site': 'admin_api',
        'token_type': 'refresh',
    }
    
    # JWT 토큰 생성
    access_token = jwt.encode(
        access_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    refresh_token = jwt.encode(
        refresh_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    # PyJWT 2.x는 문자열을 반환하지만, bytes일 수 있으므로 문자열로 변환
    if isinstance(access_token, bytes):
        access_token = access_token.decode('utf-8')
    if isinstance(refresh_token, bytes):
        refresh_token = refresh_token.decode('utf-8')
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_in': settings.JWT_ACCESS_EXPIRATION_DELTA,
    }

