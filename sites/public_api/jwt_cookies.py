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


def _effective_refresh_cookie_domain(request, domain: str | None) -> str | None:
    """
    설정 Domain 과 요청 Host 가 맞지 않으면 None(호스트 전용).
    - .localhost 는 apilocal.inde.kr 등과 불일치
    - .inde.kr 는 localhost:8001 과 불일치 → Cookie 헤더 없이 tokenrefresh 만 400 나는 원인
    """
    if not domain:
        return None
    host_only = (request.get_host().split(':')[0] or '').lower()
    if domain == '.localhost' and 'localhost' not in host_only and not host_only.startswith('127.'):
        return None
    if domain.endswith('.inde.kr') and host_only in ('localhost', '127.0.0.1'):
        return None
    return domain


def attach_public_refresh_cookie(response: HttpResponse, request, refresh_token: str) -> None:
    """응답에 refresh JWT HttpOnly 쿠키 부착. JSON 바디에는 넣지 않는 것을 권장."""
    if not refresh_token:
        return
    name = _refresh_cookie_name()
    domain = _effective_refresh_cookie_domain(request, _refresh_cookie_domain())
    samesite = getattr(settings, 'PUBLIC_JWT_REFRESH_COOKIE_SAMESITE', 'Lax') or 'Lax'
    if isinstance(samesite, str) and samesite.lower() == 'none':
        samesite = 'None'
    # Chromium: SameSite=None 은 Secure 필수. HTTP 로컬에서는 Secure=False → 쿠키 전부 거절됨
    if samesite == 'None' and not request.is_secure():
        samesite = 'Lax'
    kwargs = {
        'key': name,
        'value': refresh_token,
        'max_age': int(settings.JWT_REFRESH_EXPIRATION_DELTA),
        'httponly': True,
        'secure': bool(request.is_secure()),
        'samesite': samesite,
        'path': '/',
    }
    if domain:
        kwargs['domain'] = domain
    response.set_cookie(**kwargs)


def clear_public_refresh_cookie(response: HttpResponse, request) -> None:
    """로그아웃 등 — refresh 쿠키 삭제 (설정 시 domain/path 일치 필수)."""
    name = _refresh_cookie_name()
    domain = _effective_refresh_cookie_domain(request, _refresh_cookie_domain())
    if domain:
        response.delete_cookie(name, path='/', domain=domain)
    else:
        response.delete_cookie(name, path='/')
