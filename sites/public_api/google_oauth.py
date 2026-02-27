"""
Google OAuth 2.0 로그인/회원가입
- redirect: 사용자를 Google 동의 화면으로 보냄
- callback: code 교환 → 사용자 정보 조회 → PublicMemberShip 생성/조회 → JWT 발급 → 프론트 리다이렉트
"""
import logging
import os
import urllib.parse
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.views import View
import requests

from core.models import AuditLog
from sites.public_api.models import PublicMemberShip
from sites.public_api.utils import create_public_jwt_tokens

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
SCOPE = 'openid email profile'


def _get_client_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    if x:
        return x.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _frontend_callback_url():
    base = (getattr(settings, 'PUBLIC_VERIFY_BASE_URL', '') or '').strip().rstrip('/')
    if not base:
        base = 'http://localhost:3001'  # 로컬 개발 기본값
    return f'{base}/auth/callback'


class GoogleRedirectView(View):
    """Google 로그인/회원가입 시작 → Google 동의 화면으로 리다이렉트"""

    def get(self, request):
        client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '').strip()
        if not client_id:
            logger.warning('GOOGLE_OAUTH_CLIENT_ID 미설정')
            redirect_base = _frontend_callback_url().replace('/auth/callback', '')
            return HttpResponseRedirect(f'{redirect_base}/login?error=OAUTH_CONFIG')

        redirect_uri = request.build_absolute_uri('/auth/google/callback/')
        state = request.GET.get('state', '')
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': SCOPE,
            'access_type': 'offline',
            'prompt': 'consent',
        }
        if state:
            params['state'] = state
        url = f'{GOOGLE_AUTH_URL}?{urlencode(params)}'
        return HttpResponseRedirect(url)


class GoogleCallbackView(View):
    """Google에서 돌아온 callback: code 교환 → 회원 조회/생성 → JWT → 프론트 /auth/callback 로 리다이렉트"""

    def get(self, request):
        code = request.GET.get('code')
        error = request.GET.get('error')
        frontend_callback = _frontend_callback_url()

        if error:
            logger.warning('Google OAuth error: %s', error)
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_DENIED')

        if not code:
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_NO_CODE')

        client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '').strip()
        client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '').strip()
        if not client_id or not client_secret:
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_CONFIG')

        redirect_uri = request.build_absolute_uri('/auth/google/callback/')

        token_res = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10,
        )
        if token_res.status_code != 200:
            logger.warning('Google token exchange failed: %s %s', token_res.status_code, token_res.text)
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        try:
            token_data = token_res.json()
            access_token = token_data.get('access_token')
        except Exception:
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        if not access_token:
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        user_res = requests.get(
            GOOGLE_USERINFO_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        if user_res.status_code != 200:
            logger.warning('Google userinfo failed: %s', user_res.status_code)
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        try:
            user_data = user_res.json()
        except Exception:
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        google_sub = user_data.get('id') or user_data.get('sub') or ''
        email = (user_data.get('email') or '').strip()
        name = (user_data.get('name') or email.split('@')[0] or 'User').strip()[:100]

        if not email:
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_NO_EMAIL')

        member = PublicMemberShip.objects.filter(
            joined_via='GOOGLE', sns_provider_uid=google_sub
        ).first()
        if member:
            pass
        else:
            by_email = PublicMemberShip.objects.filter(email=email).first()
            if by_email:
                if by_email.joined_via == 'LOCAL':
                    return HttpResponseRedirect(
                        f'{frontend_callback}?error=EMAIL_ALREADY_REGISTERED'
                    )
                by_email.sns_provider_uid = google_sub
                by_email.save(update_fields=['sns_provider_uid'])
                member = by_email
            else:
                nickname = (user_data.get('given_name') or name or email.split('@')[0])[:100]
                member = PublicMemberShip(
                    email=email,
                    name=name,
                    nickname=nickname,
                    phone='',
                    joined_via='GOOGLE',
                    sns_provider_uid=google_sub,
                    password=None,
                    email_verified=True,
                    profile_completed=False,
                    is_active=True,
                )
                member.save()
                AuditLog.objects.create(
                    user_id=member.member_sid,
                    site_slug='public_api',
                    action='create',
                    resource='publicMemberShip',
                    resource_id=member.member_sid,
                    ip_address=_get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={'status': 'success', 'action': 'register_google'},
                )

        member.last_login = timezone.now()
        member.save(update_fields=['last_login'])

        tokens = create_public_jwt_tokens(member)

        AuditLog.objects.create(
            user_id=member.member_sid,
            site_slug='public_api',
            action='login',
            resource='publicMemberShip',
            resource_id=member.member_sid,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'status': 'success', 'provider': 'google'},
        )

        state = request.GET.get('state', '')
        query_params = {
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'expires_in': str(tokens['expires_in']),
        }
        if state == 'signup':
            query_params['from'] = 'signup'
        query = urllib.parse.urlencode(query_params)
        return HttpResponseRedirect(f'{frontend_callback}?{query}')
