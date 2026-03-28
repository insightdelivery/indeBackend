"""
public_api refresh JWT — HttpOnly 쿠키 설정/삭제 (frontend_wwwRules.md §3).
"""
from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse


def _refresh_cookie_name() -> str:
    return getattr(settings, 'PUBLIC_JWT_REFRESH_COOKIE_NAME', 'refreshToken')


def _refresh_cookie_domain():
    d = getattr(settings, 'PUBLIC_JWT_REFRESH_COOKIE_DOMAIN', None)
    if d is None or (isinstance(d, str) and not d.strip()):
        return None
    return d.strip() if isinstance(d, str) else d


def attach_public_refresh_cookie(response: HttpResponse, request, refresh_token: str) -> None:
    """응답에 refresh JWT HttpOnly 쿠키 부착. JSON 바디에는 넣지 않는 것을 권장."""
    if not refresh_token:
        return
    name = _refresh_cookie_name()
    domain = _refresh_cookie_domain()
    kwargs = {
        'key': name,
        'value': refresh_token,
        'max_age': int(settings.JWT_REFRESH_EXPIRATION_DELTA),
        'httponly': True,
        'secure': bool(request.is_secure()),
        'samesite': getattr(settings, 'PUBLIC_JWT_REFRESH_COOKIE_SAMESITE', 'Lax'),
        'path': '/',
    }
    if domain:
        kwargs['domain'] = domain
    response.set_cookie(**kwargs)


def clear_public_refresh_cookie(response: HttpResponse, request) -> None:
    """로그아웃 등 — refresh 쿠키 삭제 (설정 시 domain/path 일치 필수)."""
    name = _refresh_cookie_name()
    domain = _refresh_cookie_domain()
    if domain:
        response.delete_cookie(name, path='/', domain=domain)
    else:
        response.delete_cookie(name, path='/')
