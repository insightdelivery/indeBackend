"""
네이버 로그인(NAVER Login API) 회원가입/로그인
- redirect: 사용자를 네이버 동의 화면으로 보냄
- callback: code 교환 → 사용자 정보 조회 → PublicMemberShip 생성/조회 → JWT 발급 → 프론트 리다이렉트
- 규칙: _docsRules/1_planDoc/snsNaverJoin.md
"""
import base64
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

NAVER_AUTH_URL = 'https://nid.naver.com/oauth2.0/authorize'
NAVER_TOKEN_URL = 'https://nid.naver.com/oauth2.0/token'
NAVER_USERINFO_URL = 'https://openapi.naver.com/v1/nid/me'


def _get_client_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    if x:
        return x.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _frontend_callback_url():
    base = (getattr(settings, 'PUBLIC_VERIFY_BASE_URL', '') or '').strip().rstrip('/')
    if not base:
        base = 'http://localhost:3001'
    return f'{base}/auth/callback'


class NaverRedirectView(View):
    """네이버 로그인/회원가입 시작 → 네이버 동의 화면으로 리다이렉트"""

    def get(self, request):
        client_id = os.getenv('NAVER_OAUTH_CLIENT_ID', '').strip()
        if not client_id:
            logger.warning('NAVER_OAUTH_CLIENT_ID 미설정')
            redirect_base = _frontend_callback_url().replace('/auth/callback', '')
            return HttpResponseRedirect(f'{redirect_base}/login?error=OAUTH_CONFIG')

        redirect_uri = request.build_absolute_uri('/auth/naver/callback/')
        frontend_state = request.GET.get('state', '')
        state_b64 = base64.urlsafe_b64encode(redirect_uri.encode()).decode().rstrip('=')
        state = f'{frontend_state}:{state_b64}' if frontend_state else state_b64
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'state': state,
        }
        url = f'{NAVER_AUTH_URL}?{urlencode(params)}'
        return HttpResponseRedirect(url)


class NaverCallbackView(View):
    """네이버에서 돌아온 callback: code 교환 → 회원 조회/생성 → JWT → 프론트 /auth/callback 리다이렉트"""

    def get(self, request):
        code = request.GET.get('code')
        error = request.GET.get('error')
        frontend_callback = _frontend_callback_url()
        logger.info('[NAVER_OAUTH] callback entered code=%s error=%s', 'yes' if code else 'no', error)

        if error:
            logger.warning('Naver OAuth error: %s', error)
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_DENIED')

        if not code:
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_NO_CODE')

        client_id = os.getenv('NAVER_OAUTH_CLIENT_ID', '').strip()
        client_secret = os.getenv('NAVER_OAUTH_CLIENT_SECRET', '').strip()
        if not client_id or not client_secret:
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_CONFIG')

        state_param = request.GET.get('state', '')
        if ':' in state_param:
            _, state_b64 = state_param.split(':', 1)
        else:
            state_b64 = state_param
        try:
            padding = 4 - len(state_b64) % 4
            if padding != 4:
                state_b64 += '=' * padding
            redirect_uri = base64.urlsafe_b64decode(state_b64).decode()
        except Exception:
            redirect_uri = request.build_absolute_uri('/auth/naver/callback/')
        logger.info('Naver OAuth token exchange redirect_uri=%s', redirect_uri)

        token_res = requests.get(
            NAVER_TOKEN_URL,
            params={
                'grant_type': 'authorization_code',
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'code': code,
                'state': state_param,
            },
            timeout=10,
        )
        if token_res.status_code != 200:
            logger.warning(
                'Naver token exchange failed: status=%s body=%s redirect_uri=%s',
                token_res.status_code, token_res.text[:300], redirect_uri,
            )
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        try:
            token_data = token_res.json()
        except Exception as e:
            logger.warning('Naver OAuth: token response JSON parse failed: %s body=%s', e, token_res.text[:500])
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        if token_data.get('error'):
            logger.warning(
                'Naver OAuth: token response has error: error=%s description=%s',
                token_data.get('error'), token_data.get('error_description', ''),
            )
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        access_token = token_data.get('access_token')
        if not access_token:
            logger.warning('Naver OAuth: no access_token in response keys=%s', list(token_data.keys()))
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        user_res = requests.get(
            NAVER_USERINFO_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        if user_res.status_code != 200:
            logger.warning('Naver userinfo failed: status=%s body=%s', user_res.status_code, user_res.text[:300])
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        try:
            raw = user_res.json()
        except Exception as e:
            logger.warning('Naver OAuth: userinfo JSON parse failed: %s body=%s', e, user_res.text[:500])
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        if raw.get('resultcode') != '00':
            logger.warning('Naver userinfo resultcode=%s message=%s', raw.get('resultcode'), raw.get('message'))
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        user_data = raw.get('response') or {}
        naver_id = (user_data.get('id') or '').strip() or str(user_data.get('id', ''))
        if not naver_id:
            logger.warning('Naver userinfo: response.id missing')
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')
        email = (user_data.get('email') or '').strip()
        name = (user_data.get('name') or email.split('@')[0] or 'User').strip()[:100]
        nickname = (user_data.get('nickname') or name or email.split('@')[0] or 'User').strip()[:100]
        phone = (user_data.get('mobile') or '').strip()[:20] or ''

        if not email:
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_NO_EMAIL')

        member = PublicMemberShip.objects.filter(
            joined_via='NAVER', sns_provider_uid=naver_id
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
                by_email.sns_provider_uid = naver_id
                by_email.save(update_fields=['sns_provider_uid'])
                member = by_email
            else:
                member = PublicMemberShip(
                    email=email,
                    name=name,
                    nickname=nickname,
                    phone=phone,
                    joined_via='NAVER',
                    sns_provider_uid=naver_id,
                    password=None,
                    email_verified=True,
                    profile_completed=False,
                    is_active=True,
                )
                member.save()
                AuditLog.objects.create(
                    user_id=str(member.member_sid),
                    site_slug='public_api',
                    action='create',
                    resource='publicMemberShip',
                    resource_id=str(member.member_sid),
                    ip_address=_get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={'status': 'success', 'action': 'register_naver'},
                )

        member.last_login = timezone.now()
        member.save(update_fields=['last_login'])

        try:
            tokens = create_public_jwt_tokens(member)
        except Exception as e:
            logger.exception('Naver OAuth: create_public_jwt_tokens failed: %s', e)
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        AuditLog.objects.create(
            user_id=str(member.member_sid),
            site_slug='public_api',
            action='login',
            resource='publicMemberShip',
            resource_id=str(member.member_sid),
            ip_address=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'status': 'success', 'provider': 'naver'},
        )

        state_param = request.GET.get('state', '')
        from_signup = state_param.split(':')[0] == 'signup' if state_param else False
        query_params = {
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'expires_in': str(tokens['expires_in']),
        }
        if from_signup:
            query_params['from'] = 'signup'
        query = urllib.parse.urlencode(query_params)
        logger.info('[NAVER_OAUTH] success, redirecting to %s', frontend_callback)
        return HttpResponseRedirect(f'{frontend_callback}?{query}')
