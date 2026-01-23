"""
Admin API 유틸리티 함수
JWT 토큰 생성 등
"""
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from core.models import Account


def create_admin_jwt_tokens(user: Account):
    """
    관리자용 JWT 토큰 생성
    
    Args:
        user: Account 모델 인스턴스
    
    Returns:
        dict: access_token과 refresh_token을 포함한 딕셔너리
    """
    now = datetime.utcnow()
    access_expiration = now + timedelta(seconds=settings.JWT_ACCESS_EXPIRATION_DELTA)
    refresh_expiration = now + timedelta(seconds=settings.JWT_REFRESH_EXPIRATION_DELTA)
    
    # Access Token 페이로드
    access_payload = {
        'user_id': str(user.id),
        'email': user.email,
        'name': user.name,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'exp': access_expiration,
        'iat': now,
        'site': 'admin_api',
        'token_type': 'access',
    }
    
    # Refresh Token 페이로드
    refresh_payload = {
        'user_id': str(user.id),
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

