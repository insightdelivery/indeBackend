"""
OAuth authorize `state` — redirect_uri(base64) + 선택적 로그인 후 복귀 경로 `next`.
프론트 출처(포트)와 콜백 베이스 URL이 달라도 sessionStorage 없이 `next`를 전달하기 위함.
"""
from __future__ import annotations

import base64
import logging
import re

logger = logging.getLogger(__name__)

_MAX_NEXT_LEN = 2048


def sanitize_next_path(raw: str | None) -> str | None:
    """프론트 postLoginRedirect와 동일한 수준의 open-redirect 방지."""
    if not raw or not isinstance(raw, str):
        return None
    t = raw.strip()
    if len(t) > _MAX_NEXT_LEN:
        return None
    if not t.startswith('/') or t.startswith('//'):
        return None
    if re.search(r'[\s\r\n]', t):
        return None
    if '://' in t:
        return None
    if t == '/login' or t.startswith('/login?') or t == '/register' or t.startswith('/register?'):
        return None
    return t


def build_oauth_state(frontend_state: str, redirect_uri: str, next_path: str | None) -> str:
    """
    - 로그인 복귀 경로 있음: next:{np_b64}:{ru_b64}
    - 회원가입 등: signup:{ru_b64} 또는 {prefix}:{ru_b64}
    - 기본: {ru_b64}
    """
    ru_b64 = base64.urlsafe_b64encode(redirect_uri.encode('utf-8')).decode().rstrip('=')
    safe_next = sanitize_next_path(next_path) if next_path else None
    if safe_next:
        np_b64 = base64.urlsafe_b64encode(safe_next.encode('utf-8')).decode().rstrip('=')
        return f'next:{np_b64}:{ru_b64}'
    if frontend_state:
        return f'{frontend_state}:{ru_b64}'
    return ru_b64


def parse_oauth_state_for_redirect_uri(state_param: str) -> tuple[str, str | None]:
    """
    토큰 교환용 redirect_uri 디코드 + (있으면) 프론트에 넘길 next 경로.
    반환: (redirect_uri, next_for_frontend)
    """
    if not state_param:
        return '', None

    if state_param.startswith('next:'):
        parts = state_param.split(':', 2)
        if len(parts) == 3:
            _, np_b64, ru_b64 = parts
            try:
                next_path = _decode_b64url(np_b64)
                redirect_uri = _decode_b64url(ru_b64)
                if sanitize_next_path(next_path) != next_path:
                    next_path = None
                return redirect_uri, next_path
            except Exception as e:
                logger.warning('OAuth state next: parse failed: %s', e)
        # fall through

    if ':' in state_param:
        _, ru_part = state_param.split(':', 1)
        try:
            return _decode_b64url(ru_part), None
        except Exception as e:
            logger.warning('OAuth state legacy: decode failed: %s', e)
            return '', None

    try:
        return _decode_b64url(state_param), None
    except Exception as e:
        logger.warning('OAuth state bare: decode failed: %s', e)
        return '', None


def is_signup_oauth_state(state_param: str) -> bool:
    if not state_param or state_param.startswith('next:'):
        return False
    return state_param.split(':', 1)[0] == 'signup'


def _decode_b64url(s: str) -> str:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += '=' * pad
    return base64.urlsafe_b64decode(s).decode('utf-8')
