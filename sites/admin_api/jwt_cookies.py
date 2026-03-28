"""
admin_api refresh JWT — HttpOnly 쿠키 (frontend_adminRules.md 인증 복구 정책).
공개 사이트 PUBLIC_JWT_* 와 쿠키 이름·도메인을 분리한다.
"""
from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse


def _admin_refresh_cookie_name() -> str:
    return getattr(settings, 'ADMIN_JWT_REFRESH_COOKIE_NAME', 'adminRefreshToken')


def _admin_refresh_cookie_domain():
    d = getattr(settings, 'ADMIN_JWT_REFRESH_COOKIE_DOMAIN', None)
    if d is None or (isinstance(d, str) and not d.strip()):
        return None
    return d.strip() if isinstance(d, str) else d


def attach_admin_refresh_cookie(response: HttpResponse, request, refresh_token: str) -> None:
    """응답에 관리자 refresh JWT HttpOnly 쿠키. JSON 바디에는 refresh_token 을 넣지 않는다."""
    if not refresh_token:
        return
    name = _admin_refresh_cookie_name()
    domain = _admin_refresh_cookie_domain()
    kwargs = {
        'key': name,
        'value': refresh_token,
        'max_age': int(settings.JWT_REFRESH_EXPIRATION_DELTA),
        'httponly': True,
        'secure': bool(request.is_secure()),
        'samesite': getattr(settings, 'ADMIN_JWT_REFRESH_COOKIE_SAMESITE', 'Lax'),
        'path': '/',
    }
    if domain:
        kwargs['domain'] = domain
    response.set_cookie(**kwargs)


def clear_admin_refresh_cookie(response: HttpResponse, request) -> None:
    name = _admin_refresh_cookie_name()
    domain = _admin_refresh_cookie_domain()
    if domain:
        response.delete_cookie(name, path='/', domain=domain)
    else:
        response.delete_cookie(name, path='/')
