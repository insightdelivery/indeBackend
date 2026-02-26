"""
Public API 유틸리티 함수
JWT 토큰 생성/검증 (PublicMemberShip 기반)
"""
import jwt
from datetime import datetime, timedelta
from django.conf import settings


def get_token_from_cookie(request):
    """쿠키에서 access_token, refresh_token 추출. (Bearer 헤더는 axios에서 처리)"""
    access = request.COOKIES.get('accessToken') or ''
    refresh = request.COOKIES.get('refreshToken') or ''
    return (access.strip(), refresh.strip())


def get_token_from_request(request):
    """Authorization Bearer 또는 쿠키에서 access_token 추출"""
    auth = request.META.get('HTTP_AUTHORIZATION') or ''
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    token, _ = get_token_from_cookie(request)
    return token


def verify_jwt_token(token, token_type='access'):
    """JWT 검증 후 payload 반환. 실패 시 None."""
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[getattr(settings, 'JWT_ALGORITHM', 'HS256')],
        )
        if payload.get('token_type') != token_type or payload.get('site') != 'public_api':
            return None
        return payload
    except Exception:
        return None


def create_public_jwt_tokens(user):
    """
    공개 API용 JWT 토큰 생성
    user: PublicMemberShip 또는 id(member_sid), email, name 속성을 가진 객체
    """
    user_id = getattr(user, 'member_sid', None) or getattr(user, 'id', None)
    email = getattr(user, 'email', '')
    name = getattr(user, 'name', '') or ''
    now = datetime.utcnow()
    access_expiration = now + timedelta(seconds=settings.JWT_ACCESS_EXPIRATION_DELTA)
    refresh_expiration = now + timedelta(seconds=settings.JWT_REFRESH_EXPIRATION_DELTA)

    access_payload = {
        'user_id': str(user_id),
        'email': email,
        'name': name,
        'exp': access_expiration,
        'iat': now,
        'site': 'public_api',
        'token_type': 'access',
    }
    refresh_payload = {
        'user_id': str(user_id),
        'exp': refresh_expiration,
        'iat': now,
        'site': 'public_api',
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

