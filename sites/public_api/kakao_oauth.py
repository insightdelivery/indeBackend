"""
카카오 로그인(Kakao Login REST API) 회원가입/로그인
- redirect: 카카오 인가 화면 (기본 scope 미요청 — KAKAO_OAUTH_SCOPE 로만 지정)
- callback: code → 토큰 → v2/user/me → PublicMemberShip → JWT → 프론트 /auth/callback
- 규칙: _docsRules/1_planDoc/snsKaKaoJoin.md
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
from sites.public_api.utils import create_public_jwt_tokens, create_oauth_pending_token
from sites.public_api.jwt_cookies import attach_public_refresh_cookie

logger = logging.getLogger(__name__)

KAKAO_AUTH_URL = 'https://kauth.kakao.com/oauth/authorize'
KAKAO_TOKEN_URL = 'https://kauth.kakao.com/oauth/token'
KAKAO_USER_ME_URL = 'https://kapi.kakao.com/v2/user/me'

# 동의항목 미비·비즈앱 심사 전: 인가 URL에 scope를 넣지 않음. 필요 시 env만 사용.
# 이메일 미동의 시 DB unique용 내부 플레이스홀더(실제 수신 불가). 심사 후 scope+프로필로 보강 예정.
PLACEHOLDER_EMAIL_DOMAIN = 'oauth-noemail.invalid'


def _get_client_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    if x:
        return x.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _frontend_callback_url():
    base = (getattr(settings, 'PUBLIC_VERIFY_BASE_URL', '') or '').strip().rstrip('/')
    if not base:
        base = 'http://localhost:3000'
    return f'{base}/auth/callback'


def _kakao_scope():
    return (os.getenv('KAKAO_OAUTH_SCOPE') or '').strip()


class KakaoRedirectView(View):
    """카카오 로그인/회원가입 시작 → 카카오 인가 URL로 리다이렉트"""

    def get(self, request):
        client_id = os.getenv('KAKAO_OAUTH_CLIENT_ID', '').strip()
        if not client_id:
            logger.warning('KAKAO_OAUTH_CLIENT_ID 미설정')
            redirect_base = _frontend_callback_url().replace('/auth/callback', '')
            return HttpResponseRedirect(f'{redirect_base}/login?error=OAUTH_CONFIG')

        redirect_uri = request.build_absolute_uri('/auth/kakao/callback/')
        frontend_state = request.GET.get('state', '')
        state_b64 = base64.urlsafe_b64encode(redirect_uri.encode()).decode().rstrip('=')
        state = f'{frontend_state}:{state_b64}' if frontend_state else state_b64

        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'state': state,
        }
        scope = _kakao_scope()
        if scope:
            params['scope'] = scope

        url = f'{KAKAO_AUTH_URL}?{urlencode(params)}'
        return HttpResponseRedirect(url)


class KakaoCallbackView(View):
    """카카오 콜백: 토큰 교환 → 사용자 정보 → JWT → 프론트 /auth/callback"""

    def get(self, request):
        code = request.GET.get('code')
        error = request.GET.get('error')
        frontend_callback = _frontend_callback_url()
        logger.info('[KAKAO_OAUTH] callback code=%s error=%s', 'yes' if code else 'no', error)

        if error:
            logger.warning('Kakao OAuth error: %s', error)
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_DENIED')

        if not code:
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_NO_CODE')

        client_id = os.getenv('KAKAO_OAUTH_CLIENT_ID', '').strip()
        client_secret = os.getenv('KAKAO_OAUTH_CLIENT_SECRET', '').strip()
        if not client_id:
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
            redirect_uri = request.build_absolute_uri('/auth/kakao/callback/')
        logger.info('Kakao OAuth token exchange redirect_uri=%s', redirect_uri)

        token_body = {
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'code': code,
        }
        if client_secret:
            token_body['client_secret'] = client_secret

        token_res = requests.post(
            KAKAO_TOKEN_URL,
            data=token_body,
            headers={'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'},
            timeout=10,
        )
        if token_res.status_code != 200:
            logger.warning(
                'Kakao token exchange failed: status=%s body=%s redirect_uri=%s',
                token_res.status_code, token_res.text[:300], redirect_uri,
            )
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        try:
            token_data = token_res.json()
        except Exception as e:
            logger.warning('Kakao OAuth: token JSON parse failed: %s body=%s', e, token_res.text[:500])
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        if token_data.get('error'):
            logger.warning(
                'Kakao OAuth token error: %s %s',
                token_data.get('error'), token_data.get('error_description', ''),
            )
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        access_token = token_data.get('access_token')
        if not access_token:
            logger.warning('Kakao OAuth: no access_token keys=%s', list(token_data.keys()))
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        user_res = requests.get(
            KAKAO_USER_ME_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        if user_res.status_code != 200:
            logger.warning('Kakao user/me failed: status=%s body=%s', user_res.status_code, user_res.text[:300])
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        try:
            raw = user_res.json()
        except Exception as e:
            logger.warning('Kakao user/me JSON parse failed: %s body=%s', e, user_res.text[:500])
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        kakao_uid = raw.get('id')
        if kakao_uid is None:
            logger.warning('Kakao user/me: id missing')
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')
        kakao_id = str(kakao_uid)

        kakao_account = raw.get('kakao_account') or {}
        email_from_provider = (kakao_account.get('email') or '').strip()
        if email_from_provider:
            email = email_from_provider
            email_verified_flag = True
        else:
            email = f'kakao-{kakao_id}@{PLACEHOLDER_EMAIL_DOMAIN}'
            email_verified_flag = False

        profile = kakao_account.get('profile') or {}
        nickname = (profile.get('nickname') or '').strip()
        name = (
            kakao_account.get('name')
            or nickname
            or (email_from_provider.split('@')[0] if email_from_provider else '')
            or 'User'
        )
        name = str(name).strip()[:100]
        if not nickname:
            nickname = (name or 'User').strip()[:100]
        phone_raw = (kakao_account.get('phone_number') or '').strip()
        phone = phone_raw[:20] if phone_raw else ''

        member = PublicMemberShip.objects.filter(
            joined_via='KAKAO', sns_provider_uid=kakao_id
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
                by_email.sns_provider_uid = kakao_id
                by_email.save(update_fields=['sns_provider_uid'])
                member = by_email
            else:
                pending = create_oauth_pending_token(
                    'KAKAO', kakao_id, email, name, nickname
                )
                q = urllib.parse.urlencode({'temp_token': pending})
                return HttpResponseRedirect(f'{frontend_callback}?{q}')

        member.last_login = timezone.now()
        member.save(update_fields=['last_login'])

        try:
            tokens = create_public_jwt_tokens(member)
        except Exception as e:
            logger.exception('Kakao OAuth: create_public_jwt_tokens failed: %s', e)
            return HttpResponseRedirect(f'{frontend_callback}?error=OAUTH_FAILED')

        AuditLog.objects.create(
            user_id=str(member.member_sid),
            site_slug='public_api',
            action='login',
            resource='publicMemberShip',
            resource_id=str(member.member_sid),
            ip_address=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'status': 'success', 'provider': 'kakao'},
        )

        from_signup = state_param.split(':')[0] == 'signup' if state_param else False
        query_params = {
            'access_token': tokens['access_token'],
            'expires_in': str(tokens['expires_in']),
        }
        if from_signup:
            query_params['from'] = 'signup'
        query = urllib.parse.urlencode(query_params)
        logger.info('[KAKAO_OAUTH] success redirect %s', frontend_callback)
        response = HttpResponseRedirect(f'{frontend_callback}?{query}')
        attach_public_refresh_cookie(response, request, tokens['refresh_token'])
        return response
