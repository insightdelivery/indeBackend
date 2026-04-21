"""
공개 API 뷰 (PublicMemberShip 기반 일반 회원가입/로그인)
"""
import logging
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.utils import timezone
from core.models import AuditLog
from sites.public_api.models import PhoneSmsVerification, PublicMemberShip
from sites.public_api.phone_normalize import is_valid_kr_mobile, normalize_phone_kr, phone_already_registered
from sites.public_api.serializers import RegisterSerializer, LoginSerializer
from sites.public_api.utils import (
    create_public_jwt_tokens,
    get_token_from_cookie,
    get_token_from_request,
    verify_jwt_token,
    verify_oauth_pending_token,
)
from sites.public_api.jwt_cookies import attach_public_refresh_cookie, clear_public_refresh_cookie
from sites.public_api import email_verification
from sites.public_api.kakao_oauth import PLACEHOLDER_EMAIL_DOMAIN
from sites.public_api.signup_alimtalk import try_send_signup_complete_alimtalk

logger = logging.getLogger(__name__)


def _jwt_login_response(request, tokens: dict, user_payload: dict, status_code: int) -> Response:
    """access·expires·user는 JSON, refresh는 HttpOnly 쿠키만 (frontend_wwwRules.md)."""
    if getattr(settings, 'PUBLIC_JWT_DEBUG_LOG_TOKENS', settings.DEBUG):
        logger.warning(
            '[JWT_DEBUG][login] access_token=%s refresh_token=%s (refresh는 응답 Set-Cookie로만 전송)',
            tokens.get('access_token', ''),
            tokens.get('refresh_token', ''),
        )
    resp = Response(
        {
            'access_token': tokens['access_token'],
            'expires_in': tokens['expires_in'],
            'user': user_payload,
        },
        status=status_code,
    )
    attach_public_refresh_cookie(resp, request, tokens['refresh_token'])
    return resp


# 회원정보 휴대폰 변경 SMS 인증 완료 후 저장까지 허용 시간 (wwwMypage_userInfo §5.2)
PROFILE_PHONE_VERIFY_MAX_AGE_SEC = 15 * 60


def _check_profile_phone_verified_for_change(member: PublicMemberShip, new_phone_stripped: str):
    """
    저장하려는 번호가 기존과 다르면 profile_phone SMS 인증 필수.
    통과 시 None, 실패 시 Response.
    """
    old_norm = normalize_phone_kr(member.phone or '')
    new_norm = normalize_phone_kr(new_phone_stripped)
    if old_norm == new_norm:
        return None
    if not is_valid_kr_mobile(new_norm):
        return Response(
            {'error': '올바른 휴대폰 번호를 입력해 주세요.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    row = (
        PhoneSmsVerification.objects.filter(
            phone=new_norm,
            purpose=PhoneSmsVerification.PURPOSE_PROFILE_PHONE,
            verified=True,
            verified_at__isnull=False,
        )
        .order_by('-verified_at')
        .first()
    )
    if not row:
        return Response(
            {'error': '변경된 휴대폰 번호는 문자 인증 후 저장할 수 있습니다.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if (timezone.now() - row.verified_at) > timedelta(seconds=PROFILE_PHONE_VERIFY_MAX_AGE_SEC):
        return Response(
            {'error': '휴대폰 인증이 만료되었습니다. 인증번호를 다시 요청해 주세요.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def _consume_profile_phone_verification(new_norm: str) -> None:
    if not new_norm:
        return
    PhoneSmsVerification.objects.filter(
        phone=new_norm,
        purpose=PhoneSmsVerification.PURPOSE_PROFILE_PHONE,
    ).delete()


def _user_response(member):
    """PublicMemberShip -> API 응답 user 객체 (회원정보 수정 폼에 필요한 필드 포함)"""
    return {
        'id': member.member_sid,
        'email': member.email,
        'name': member.name,
        'nickname': member.nickname,
        'phone': member.phone,
        'position': member.position or None,
        'birth_year': member.birth_year,
        'birth_month': member.birth_month,
        'birth_day': member.birth_day,
        'region_type': member.region_type or None,
        'region_domestic': member.region_domestic or None,
        'region_foreign': member.region_foreign or None,
        'profile_completed': member.profile_completed,
        'email_verified': member.email_verified,
        'newsletter_agree': bool(member.newsletter_agree),
        'joined_via': member.joined_via,
        'is_staff': getattr(member, 'is_staff', False),
        'created_at': member.created_at.isoformat() if member.created_at else None,
        'updated_at': member.updated_at.isoformat() if member.updated_at else None,
    }


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR', '')


def _apply_profile_email_update(member, data):
    """
    요청 body의 email이 현재와 다르면 형식·중복 검사 후 member.email 갱신, email_verified=False.
    카카오+이메일 미인증은 반드시 유효한 이메일이 body에 있어야 함.
    Returns (error Response or None, send_verification_after_save: bool).
    """
    raw = data.get('email') if isinstance(data.get('email'), str) else ''
    raw = (raw or '').strip()
    old_email = (member.email or '').lower()

    if member.joined_via == 'KAKAO' and not member.email_verified:
        if not raw:
            return Response(
                {'error': '이메일을 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            ), False

    if not raw:
        if not (member.email or '').strip():
            return Response(
                {'error': '이메일을 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            ), False
        return None, False

    try:
        validate_email(raw)
    except ValidationError:
        return Response(
            {'error': '올바른 이메일 형식이 아닙니다.'},
            status=status.HTTP_400_BAD_REQUEST,
        ), False

    new_email = raw.lower()
    if new_email.endswith(f'@{PLACEHOLDER_EMAIL_DOMAIN}'):
        return Response(
            {'error': '본인 이메일 주소를 입력해 주세요.'},
            status=status.HTTP_400_BAD_REQUEST,
        ), False

    if new_email == old_email:
        return None, False

    if PublicMemberShip.objects.filter(email__iexact=new_email).exclude(member_sid=member.member_sid).exists():
        return Response(
            {'error': '이미 사용 중인 이메일입니다. 다른 이메일을 입력해 주세요.'},
            status=status.HTTP_400_BAD_REQUEST,
        ), False

    member.email = new_email
    member.email_verified = False
    return None, True


def _send_profile_verification_email(member):
    token = email_verification.create_verification_token(member.email)
    verify_url = email_verification.get_verification_link(token)
    sent = email_verification.send_verification_email(member.email, verify_url)
    if not sent:
        logger.warning('프로필 완료 후 인증 메일 발송 실패: email=%s', member.email)
    return sent


class RegisterView(APIView):
    """회원 가입 API (publicMemberShip 테이블, 일반 가입)"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': '입력값이 올바르지 않습니다.',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        phone_norm = normalize_phone_kr(data['phone'])
        if not is_valid_kr_mobile(phone_norm):
            return Response(
                {'error': '올바른 휴대폰 번호를 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not PhoneSmsVerification.objects.filter(
            phone=phone_norm, verified=True, purpose=PhoneSmsVerification.PURPOSE_SIGNUP
        ).exists():
            return Response(
                {'error': '휴대폰 인증을 완료한 후 회원가입할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if phone_already_registered(phone_norm):
            return Response(
                {'error': '이미 가입된 휴대폰 번호입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            member = PublicMemberShip(
                email=data['email'],
                name=data['name'],
                nickname=data['nickname'],
                phone=phone_norm,
                position=data.get('position') or '',
                birth_year=data.get('birth_year'),
                birth_month=data.get('birth_month'),
                birth_day=data.get('birth_day'),
                region_type='FOREIGN' if data.get('is_overseas') else ('DOMESTIC' if data.get('region') else None),
                region_domestic=data.get('region') if not data.get('is_overseas') else None,
                region_foreign=data.get('region') if data.get('is_overseas') else None,
                joined_via='LOCAL',
                newsletter_agree=data.get('newsletter_agree', False),
                profile_completed=True,
                email_verified=True,
                is_active=True,
            )
            member.set_password(data['password'])
            member.save()

            try_send_signup_complete_alimtalk(
                phone=member.phone or phone_norm,
                member_name=member.name or '',
            )

            PhoneSmsVerification.objects.filter(phone=phone_norm).delete()

            tokens = create_public_jwt_tokens(member)

            AuditLog.objects.create(
                user_id=member.member_sid,
                site_slug='public_api',
                action='create',
                resource='publicMemberShip',
                resource_id=member.member_sid,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'status': 'success', 'action': 'register'},
            )
            return _jwt_login_response(
                request,
                tokens,
                _user_response(member),
                status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({
                'error': f'회원 가입 처리 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(APIView):
    """로그인 API (PublicMemberShip, 일반 로그인)"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': '입력값이 올바르지 않습니다.',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            member = PublicMemberShip.objects.get(email=email, is_active=True, joined_via='LOCAL')
        except PublicMemberShip.DoesNotExist:
            return Response({
                'error': '이메일 또는 비밀번호가 올바르지 않습니다.'
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not member.check_password(password):
            AuditLog.objects.create(
                user_id=member.member_sid,
                site_slug='public_api',
                action='login',
                resource='publicMemberShip',
                resource_id=member.member_sid,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'status': 'failed', 'reason': 'invalid_password'}
            )
            return Response({
                'error': '이메일 또는 비밀번호가 올바르지 않습니다.'
            }, status=status.HTTP_401_UNAUTHORIZED)

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
            details={'status': 'success'}
        )
        return _jwt_login_response(
            request,
            tokens,
            _user_response(member),
            status.HTTP_200_OK,
        )


class PublicLogoutView(APIView):
    """POST /auth/logout — refresh HttpOnly 쿠키 삭제 (CURSOR_apiLoginRules.md)."""

    permission_classes = [AllowAny]

    def post(self, request):
        resp = Response({'success': True}, status=status.HTTP_200_OK)
        clear_public_refresh_cookie(resp, request)
        return resp


class OAuthPendingClaimsView(APIView):
    """POST /auth/oauth-pending-claims — temp_token 검증 후 JWT에 담긴 SNS 예비 프로필(프리필용)."""

    permission_classes = [AllowAny]

    def post(self, request):
        temp_token = (request.data.get('temp_token') or request.data.get('tempToken') or '').strip()
        payload = verify_oauth_pending_token(temp_token)
        if not payload:
            return Response(
                {'error': '유효하지 않거나 만료된 가입 세션입니다. 다시 소셜 로그인을 시도해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        email = (payload.get('email') or '').strip()
        name = (payload.get('name') or '').strip()
        nickname = (payload.get('nickname') or '').strip()
        provider = (payload.get('provider') or '').upper()
        kakao_ph = provider == 'KAKAO' and email.lower().endswith(f'@{PLACEHOLDER_EMAIL_DOMAIN}')
        return Response(
            {
                'email': email,
                'name': name,
                'nickname': nickname,
                'provider': provider,
                'kakao_placeholder_email': kakao_ph,
            },
            status=status.HTTP_200_OK,
        )


class SignupEmailAvailabilityView(APIView):
    """POST /auth/signup-email-availability — 비로그인 SNS 가입 단계에서 이메일 중복 여부."""

    permission_classes = [AllowAny]

    def post(self, request):
        raw = (request.data.get('email') or '').strip()
        if not raw:
            return Response(
                {'available': False, 'error': '이메일을 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_email(raw)
        except ValidationError:
            return Response(
                {'available': False, 'error': '올바른 이메일 형식이 아닙니다.'},
                status=status.HTTP_200_OK,
            )
        el = raw.lower()
        if el.endswith(f'@{PLACEHOLDER_EMAIL_DOMAIN}'):
            return Response(
                {'available': False, 'error': '본인 이메일 주소를 입력해 주세요.'},
                status=status.HTTP_200_OK,
            )
        taken = PublicMemberShip.objects.filter(email__iexact=el).exists()
        if taken:
            return Response(
                {'available': False, 'error': '이미 사용 중인 이메일입니다.'},
                status=status.HTTP_200_OK,
            )
        return Response({'available': True}, status=status.HTTP_200_OK)


class OAuthCompleteSignupView(APIView):
    """SNS 최초 가입: temp_token(oauth_pending JWT) + 휴대폰 SMS 인증 완료 후 회원 생성 및 JWT (userJoinPlan)."""

    permission_classes = [AllowAny]

    def post(self, request):
        temp_token = (request.data.get('temp_token') or request.data.get('tempToken') or '').strip()
        phone_raw = (request.data.get('phone') or '').strip()
        payload = verify_oauth_pending_token(temp_token)
        if not payload:
            return Response(
                {'error': '유효하지 않거나 만료된 가입 세션입니다. 다시 소셜 로그인을 시도해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        phone_norm = normalize_phone_kr(phone_raw)
        if not is_valid_kr_mobile(phone_norm):
            return Response(
                {'error': '올바른 휴대폰 번호를 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not PhoneSmsVerification.objects.filter(
            phone=phone_norm, verified=True, purpose=PhoneSmsVerification.PURPOSE_SIGNUP
        ).exists():
            return Response(
                {'error': '휴대폰 인증을 완료한 후 진행해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if phone_already_registered(phone_norm):
            return Response(
                {'error': '이미 가입된 휴대폰 번호입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        provider = (payload.get('provider') or '').upper()
        if provider not in ('GOOGLE', 'NAVER', 'KAKAO'):
            return Response({'error': '지원하지 않는 가입 경로입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        pid = (payload.get('provider_id') or '').strip()
        if not pid:
            return Response({'error': '유효하지 않은 가입 세션입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        if PublicMemberShip.objects.filter(joined_via=provider, sns_provider_uid=pid).exists():
            return Response({'error': '이미 가입된 소셜 계정입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        payload_email = (payload.get('email') or '').strip()
        req_email = (request.data.get('email') or '').strip()
        email = req_email or payload_email
        if not email:
            return Response(
                {'error': '이메일 정보가 없습니다. 다시 소셜 로그인을 시도해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {'error': '올바른 이메일 형식이 아닙니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        el = email.lower()
        if el.endswith(f'@{PLACEHOLDER_EMAIL_DOMAIN}'):
            return Response(
                {'error': '본인 이메일 주소를 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if PublicMemberShip.objects.filter(email__iexact=el).exists():
            return Response({'error': '이미 사용 중인 이메일입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        raw_name = (request.data.get('name') or '').strip()
        name = (raw_name or (payload.get('name') or '').strip() or 'User')[:100]
        if not name.strip():
            name = 'User'
        raw_nick = (request.data.get('nickname') or '').strip()
        nickname = (raw_nick or (payload.get('nickname') or '').strip() or name)[:100]
        if not nickname.strip():
            nickname = name
        email_verified = True
        raw_news = request.data.get('newsletter_agree')
        if raw_news is None:
            newsletter_agree = True
        elif isinstance(raw_news, bool):
            newsletter_agree = raw_news
        elif isinstance(raw_news, str):
            newsletter_agree = raw_news.strip().lower() in ('1', 'true', 'yes', 'y')
        else:
            newsletter_agree = bool(raw_news)
        try:
            member = PublicMemberShip(
                email=email,
                name=name,
                nickname=nickname,
                phone=phone_norm,
                joined_via=provider,
                sns_provider_uid=pid,
                password=None,
                email_verified=email_verified,
                profile_completed=True,
                is_active=True,
                newsletter_agree=newsletter_agree,
            )
            member.save()
        except Exception as e:
            logger.exception('OAuthCompleteSignupView: save failed: %s', e)
            return Response(
                {'error': '회원 가입 처리 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        try_send_signup_complete_alimtalk(
            phone=member.phone or phone_norm,
            member_name=member.name or '',
        )
        PhoneSmsVerification.objects.filter(phone=phone_norm).delete()
        tokens = create_public_jwt_tokens(member)
        AuditLog.objects.create(
            user_id=member.member_sid,
            site_slug='public_api',
            action='create',
            resource='publicMemberShip',
            resource_id=member.member_sid,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'status': 'success', 'action': 'oauth_phone_complete', 'provider': provider.lower()},
        )
        return _jwt_login_response(
            request,
            tokens,
            _user_response(member),
            status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    """이메일 인증 처리 (메일 링크 클릭 또는 프론트에서 토큰 전달)"""
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token', '').strip()
        return self._verify(token)

    def post(self, request):
        token = (request.data.get('token') or '').strip()
        return self._verify(token)

    def _verify(self, token):
        if not token:
            return Response({
                'error': '인증 토큰이 없습니다.',
            }, status=status.HTTP_400_BAD_REQUEST)
        email = email_verification.verify_verification_token(token)
        if not email:
            return Response({
                'error': '유효하지 않거나 만료된 링크입니다. 다시 로그인하여 인증 메일을 재발송해 주세요.',
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            member = PublicMemberShip.objects.get(email=email, is_active=True)
        except PublicMemberShip.DoesNotExist:
            return Response({
                'error': '해당 회원 정보를 찾을 수 없습니다.',
            }, status=status.HTTP_404_NOT_FOUND)
        if member.email_verified:
            return Response({
                'success': True,
                'message': '이미 인증이 완료된 이메일입니다.',
            }, status=status.HTTP_200_OK)
        member.email_verified = True
        member.save(update_fields=['email_verified'])
        return Response({
            'success': True,
            'message': '이메일 인증이 완료되었습니다. 로그인해 주세요.',
        }, status=status.HTTP_200_OK)


class ResendVerificationEmailView(APIView):
    """이메일 인증 메일 다시 보내기 (로그인 페이지 등에서 사용)"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip()
        if not email:
            return Response({
                'error': '이메일을 입력해 주세요.',
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            member = PublicMemberShip.objects.get(email=email, is_active=True)
        except PublicMemberShip.DoesNotExist:
            return Response({
                'success': True,
                'message': '해당 이메일로 인증 메일을 발송했습니다. 메일함을 확인해 주세요.',
            }, status=status.HTTP_200_OK)
        if member.email_verified:
            return Response({
                'success': True,
                'message': '이미 인증이 완료된 이메일입니다. 로그인해 주세요.',
            }, status=status.HTTP_200_OK)
        token = email_verification.create_verification_token(member.email)
        verify_url = email_verification.get_verification_link(token)
        sent = email_verification.send_verification_email(member.email, verify_url)
        if sent:
            return Response({
                'success': True,
                'message': '인증 메일을 다시 발송했습니다. 메일함(스팸함 포함)을 확인해 주세요.',
            }, status=status.HTTP_200_OK)
        return Response({
            'error': '메일 발송에 실패했습니다. 잠시 후 다시 시도해 주세요.',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MeView(APIView):
    """현재 로그인한 회원 정보 (JWT 필수), PATCH로 부가정보 완료 (구글 회원가입 후)"""
    permission_classes = [AllowAny]

    def _get_member(self, request):
        token = get_token_from_request(request)
        payload = verify_jwt_token(token, token_type='access') if token else None
        if not payload:
            return None
        user_id = payload.get('user_id')
        try:
            return PublicMemberShip.objects.get(member_sid=int(user_id), is_active=True)
        except (PublicMemberShip.DoesNotExist, ValueError, TypeError):
            return None

    def get(self, request):
        member = self._get_member(request)
        if not member:
            return Response({'detail': '인증이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(_user_response(member), status=status.HTTP_200_OK)

    def patch(self, request):
        member = self._get_member(request)
        if not member:
            return Response({'detail': '인증이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        data = request.data
        err, send_verification = _apply_profile_email_update(member, data)
        if err:
            return err
        name = (data.get('name') or '').strip()
        nickname = (data.get('nickname') or '').strip()
        phone = (data.get('phone') or '').strip()
        if not name or not nickname or not phone:
            return Response(
                {'error': '이름, 닉네임, 휴대폰 번호는 필수입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        phone_err = _check_profile_phone_verified_for_change(member, phone)
        if phone_err:
            return phone_err
        old_phone_norm = normalize_phone_kr(member.phone or '')
        raw_pw = (data.get('password') or '').strip()
        if raw_pw:
            if member.joined_via != 'LOCAL':
                return Response(
                    {'error': '소셜 가입 계정은 비밀번호를 변경할 수 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if len(raw_pw) < 8:
                return Response(
                    {'error': '비밀번호는 8자 이상 입력해 주세요.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            member.password = make_password(raw_pw)
        member.name = name[:100]
        member.nickname = nickname[:100]
        member.phone = phone[:20]
        member.position = (data.get('position') or '')[:100] or None
        member.birth_year = data.get('birth_year') or None
        member.birth_month = data.get('birth_month') or None
        member.birth_day = data.get('birth_day') or None
        member.newsletter_agree = bool(data.get('newsletter_agree'))
        region_type = data.get('region_type')
        if region_type == 'FOREIGN':
            member.region_type = 'FOREIGN'
            member.region_domestic = None
            member.region_foreign = (data.get('region_foreign') or data.get('region') or '')[:100] or None
        elif region_type == 'DOMESTIC':
            member.region_type = 'DOMESTIC'
            member.region_foreign = None
            member.region_domestic = (data.get('region_domestic') or data.get('region') or '')[:100] or None
        else:
            member.region_type = None
            member.region_domestic = None
            member.region_foreign = None
        member.profile_completed = True
        member.save()
        new_norm = normalize_phone_kr(phone)
        if old_phone_norm != new_norm:
            _consume_profile_phone_verification(new_norm)
        if send_verification:
            _send_profile_verification_email(member)
        return Response(_user_response(member), status=status.HTTP_200_OK)


class MeEmailAvailabilityView(APIView):
    """GET /me/email-availability?email= — JWT(access) 필수, 타 회원과 중복 여부만 조회"""

    permission_classes = [AllowAny]

    def get(self, request):
        token = get_token_from_request(request)
        payload = verify_jwt_token(token, token_type='access') if token else None
        if not payload:
            return Response({'detail': '인증이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            member = PublicMemberShip.objects.get(member_sid=int(payload.get('user_id')), is_active=True)
        except (PublicMemberShip.DoesNotExist, ValueError, TypeError):
            return Response({'detail': '사용자를 찾을 수 없습니다.'}, status=status.HTTP_401_UNAUTHORIZED)

        raw = (request.query_params.get('email') or '').strip()
        if not raw:
            return Response({'available': False, 'error': '이메일을 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_email(raw)
        except ValidationError:
            return Response({'available': False, 'error': '올바른 이메일 형식이 아닙니다.'}, status=status.HTTP_200_OK)

        el = raw.lower()
        if el.endswith(f'@{PLACEHOLDER_EMAIL_DOMAIN}'):
            return Response({'available': False, 'error': '사용할 수 없는 이메일입니다.'}, status=status.HTTP_200_OK)

        if el == (member.email or '').lower():
            return Response({'available': True}, status=status.HTTP_200_OK)

        taken = PublicMemberShip.objects.filter(email__iexact=el).exclude(member_sid=member.member_sid).exists()
        if taken:
            return Response(
                {'available': False, 'error': '이미 사용 중인 이메일입니다.'},
                status=status.HTTP_200_OK,
            )
        return Response({'available': True}, status=status.HTTP_200_OK)


class VerifyProfilePasswordView(APIView):
    """
    마이페이지 회원정보 수정 전 본인 확인 — JWT(access) 필수, 비밀번호만 검증.
    소셜 가입(비밀번호 없음)은 skipped=True 로 성공 처리(프론트에서 수정 폼 바로 허용).
    비밀번호 불일치 시 400 (401 아님 — axios 인터셉터 토큰 갱신 루프 방지).
    """

    permission_classes = [AllowAny]

    def _get_member(self, request):
        token = get_token_from_request(request)
        payload = verify_jwt_token(token, token_type='access') if token else None
        if not payload:
            return None
        user_id = payload.get('user_id')
        try:
            return PublicMemberShip.objects.get(member_sid=int(user_id), is_active=True)
        except (PublicMemberShip.DoesNotExist, ValueError, TypeError):
            return None

    def post(self, request):
        member = self._get_member(request)
        if not member:
            return Response({'detail': '인증이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        if member.joined_via != 'LOCAL':
            return Response({'ok': True, 'skipped': True}, status=status.HTTP_200_OK)
        password = (request.data.get('password') or '').strip()
        if not password:
            return Response({'error': '비밀번호를 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)
        if not member.check_password(password):
            return Response({'error': '비밀번호가 일치하지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'ok': True}, status=status.HTTP_200_OK)


class ProfileCompleteView(APIView):
    """부가정보 완료 (구글 회원가입 후 등) - PUT /profile/complete/"""
    permission_classes = [AllowAny]

    def put(self, request):
        token = get_token_from_request(request)
        payload = verify_jwt_token(token, token_type='access') if token else None
        if not payload:
            return Response({'detail': '인증이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            member = PublicMemberShip.objects.get(
                member_sid=int(payload['user_id']), is_active=True
            )
        except (PublicMemberShip.DoesNotExist, ValueError, TypeError):
            return Response({'detail': '사용자를 찾을 수 없습니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        data = request.data
        err, send_verification = _apply_profile_email_update(member, data)
        if err:
            return err
        name = (data.get('name') or '').strip()
        nickname = (data.get('nickname') or '').strip()
        phone = (data.get('phone') or '').strip()
        if not name or not nickname or not phone:
            return Response(
                {'error': '이름, 닉네임, 휴대폰 번호는 필수입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        phone_err = _check_profile_phone_verified_for_change(member, phone)
        if phone_err:
            return phone_err
        old_phone_norm = normalize_phone_kr(member.phone or '')
        raw_pw = (data.get('password') or '').strip()
        if raw_pw:
            if member.joined_via != 'LOCAL':
                return Response(
                    {'error': '소셜 가입 계정은 비밀번호를 변경할 수 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if len(raw_pw) < 8:
                return Response(
                    {'error': '비밀번호는 8자 이상 입력해 주세요.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            member.password = make_password(raw_pw)
        member.name = name[:100]
        member.nickname = nickname[:100]
        member.phone = phone[:20]
        member.position = (data.get('position') or '')[:100] or None
        member.birth_year = data.get('birth_year') or None
        member.birth_month = data.get('birth_month') or None
        member.birth_day = data.get('birth_day') or None
        member.newsletter_agree = bool(data.get('newsletter_agree'))
        region_type = data.get('region_type')
        if region_type == 'FOREIGN':
            member.region_type = 'FOREIGN'
            member.region_domestic = None
            member.region_foreign = (data.get('region_foreign') or data.get('region') or '')[:100] or None
        elif region_type == 'DOMESTIC':
            member.region_type = 'DOMESTIC'
            member.region_foreign = None
            member.region_domestic = (data.get('region_domestic') or data.get('region') or '')[:100] or None
        else:
            member.region_type = None
            member.region_domestic = None
            member.region_foreign = None
        member.profile_completed = True
        member.save()
        new_norm = normalize_phone_kr(phone)
        if old_phone_norm != new_norm:
            _consume_profile_phone_verification(new_norm)
        if send_verification:
            _send_profile_verification_email(member)
        msg = '프로필이 완료되었습니다.'
        if send_verification:
            msg += ' 입력하신 이메일로 인증 메일을 발송했습니다. 메일함을 확인해 주세요.'
        extra = {'verification_email_sent': True} if send_verification else {}
        return Response(
            {'message': msg, 'user': _user_response(member), **extra},
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(APIView):
    """
    새 access 발급. refresh는 (1) HttpOnly 쿠키 또는 (2) Body refresh_token — 하위 호환.
    응답: JSON에 access_token·expires_in·user만; 새 refresh는 Set-Cookie(HttpOnly)만.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        cookie_name = getattr(settings, 'PUBLIC_JWT_REFRESH_COOKIE_NAME', 'refreshToken')
        raw_cookie_header = request.META.get('HTTP_COOKIE', '') or ''

        # tokenrefresh 400(빈 refresh) 원인 확인용 — 운영에서는 LOG 레벨·PUBLIC_JWT_TOKENREFRESH_VERBOSE_LOG 로 조절
        logger.warning(
            '[tokenrefresh] 진입 Origin=%s Referer=%s 기대쿠키명=%s COOKIES_파싱키=%s',
            request.META.get('HTTP_ORIGIN', ''),
            request.META.get('HTTP_REFERER', ''),
            cookie_name,
            list(request.COOKIES.keys()),
        )
        logger.warning(
            '[tokenrefresh] Raw Cookie 헤더 길이=%s 앞400자=%r',
            len(raw_cookie_header),
            raw_cookie_header[:400],
        )

        refresh_from_body = (data.get('refresh_token') or '').strip()
        refresh_token = refresh_from_body
        refresh_source = 'body' if refresh_token else None
        if not refresh_token:
            _, refresh_token = get_token_from_cookie(request)
            refresh_token = (refresh_token or '').strip()
            if refresh_token:
                refresh_source = 'cookie'

        verbose = getattr(settings, 'PUBLIC_JWT_TOKENREFRESH_VERBOSE_LOG', settings.DEBUG)
        if verbose and refresh_token:
            logger.warning(
                '[tokenrefresh] 수신 source=%s refresh_token 전체=%s',
                refresh_source,
                refresh_token,
            )

        debug_tokens = getattr(settings, 'PUBLIC_JWT_DEBUG_LOG_TOKENS', settings.DEBUG)
        if debug_tokens and not verbose:
            # 기존 JWT_DEBUG와 중복 방지: verbose가 켜져 있으면 위 로그만
            logger.warning(
                '[JWT_DEBUG][tokenrefresh] source=%s refresh_len=%s cookie_name=%s 이름이_Raw헤더에=%s',
                refresh_source or '없음',
                len(refresh_token) if refresh_token else 0,
                cookie_name,
                cookie_name in raw_cookie_header,
            )
            if refresh_token:
                logger.warning('[JWT_DEBUG][tokenrefresh] refresh_token=%s', refresh_token)

        if not refresh_token:
            logger.warning(
                '[tokenrefresh] refresh 없음 → HTTP 400. body_keys=%s body_refresh_token_len=%s '
                '쿠키_%s_존재=%s',
                list(data.keys()),
                len(refresh_from_body),
                cookie_name,
                cookie_name in request.COOKIES,
            )
            return Response(
                {
                    'error': 'refresh_token이 필요합니다. (HttpOnly 쿠키 또는 Body)',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        payload = verify_jwt_token(refresh_token, token_type='refresh')
        if not payload:
            return Response(
                {'error': '리프레시 토큰이 유효하지 않거나 만료되었습니다. 다시 로그인해 주세요.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        user_id = payload.get('user_id')
        if not user_id:
            return Response(
                {'error': '토큰에 사용자 정보가 없습니다.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            member = PublicMemberShip.objects.get(member_sid=int(user_id), is_active=True)
        except (PublicMemberShip.DoesNotExist, ValueError, TypeError):
            return Response(
                {'error': '사용자를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        tokens = create_public_jwt_tokens(member)
        if debug_tokens:
            logger.warning(
                '[JWT_DEBUG][tokenrefresh] 발급 완료 access_token=%s refresh_token(Set-Cookie)=%s',
                tokens.get('access_token', ''),
                tokens.get('refresh_token', ''),
            )
        resp = Response(
            {
                'access_token': tokens['access_token'],
                'expires_in': tokens['expires_in'],
                'user': _user_response(member),
            },
            status=status.HTTP_200_OK,
        )
        attach_public_refresh_cookie(resp, request, tokens['refresh_token'])
        return resp
