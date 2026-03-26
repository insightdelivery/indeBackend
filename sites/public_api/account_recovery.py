"""아이디 찾기·비밀번호 재설정 — 이메일 정규화, JWT reset_token (userIdPwFindPlan.md)."""
import secrets
from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password


def normalize_email(raw: str) -> str:
    return (raw or '').strip().lower()


def create_password_reset_jwt(user_id: int, nonce: str) -> str:
    now = datetime.utcnow()
    exp = now + timedelta(minutes=10)
    payload = {
        'token_type': 'password_reset',
        'site': 'public_api',
        'user_id': str(user_id),
        'nonce': nonce,
        'iat': now,
        'exp': exp,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token


def verify_password_reset_jwt(token: str):
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[getattr(settings, 'JWT_ALGORITHM', 'HS256')],
        )
        if payload.get('token_type') != 'password_reset' or payload.get('site') != 'public_api':
            return None
        return payload
    except Exception:
        return None


def new_password_reset_nonce() -> str:
    return secrets.token_hex(16)
