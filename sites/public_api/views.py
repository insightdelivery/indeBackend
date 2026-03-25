"""
공개 API 뷰 (PublicMemberShip 기반 일반 회원가입/로그인)
"""
import logging

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from core.models import AuditLog
from sites.public_api.models import PhoneSmsVerification, PublicMemberShip
from sites.public_api.phone_normalize import is_valid_kr_mobile, normalize_phone_kr, phone_already_registered
from sites.public_api.serializers import RegisterSerializer, LoginSerializer
from sites.public_api.utils import create_public_jwt_tokens, get_token_from_request, verify_jwt_token
from sites.public_api import email_verification
from sites.public_api.kakao_oauth import PLACEHOLDER_EMAIL_DOMAIN

logger = logging.getLogger(__name__)


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


def _apply_kakao_unverified_email(member, data):
    """
    카카오 가입 + 이메일 미인증: 부가정보 단계에서 실제 이메일 등록.
    Returns (error Response or None, send_verification_after_save: bool).
    Mutates member.email / email_verified when applicable.
    """
    if member.joined_via != 'KAKAO' or member.email_verified:
        return None, False

    raw = (data.get('email') or '').strip()
    if not raw:
        return Response(
            {'error': '이메일을 입력해 주세요.'},
            status=status.HTTP_400_BAD_REQUEST,
        ), False
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

    old_email = (member.email or '').lower()
    if PublicMemberShip.objects.filter(email=new_email).exclude(member_sid=member.member_sid).exists():
        return Response(
            {'error': '이미 사용 중인 이메일입니다. 다른 이메일을 입력해 주세요.'},
            status=status.HTTP_400_BAD_REQUEST,
        ), False

    member.email = new_email
    member.email_verified = False
    send_mail = new_email != old_email
    return None, send_mail


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
        if not PhoneSmsVerification.objects.filter(phone=phone_norm, verified=True).exists():
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
                email_verified=False,
                is_active=True,
            )
            member.set_password(data['password'])
            member.save()

            PhoneSmsVerification.objects.filter(phone=phone_norm).delete()

            token = email_verification.create_verification_token(member.email)
            verify_url = email_verification.get_verification_link(token)
            email_sent = email_verification.send_verification_email(member.email, verify_url)
            if not email_sent:
                import logging
                logging.getLogger(__name__).warning('회원가입 인증 메일 발송 실패: email=%s', member.email)

            AuditLog.objects.create(
                user_id=member.member_sid,
                site_slug='public_api',
                action='create',
                resource='publicMemberShip',
                resource_id=member.member_sid,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'status': 'success', 'action': 'register', 'email_sent': email_sent}
            )
            return Response({
                'success': True,
                'message': '회원가입이 완료되었습니다. 이메일 인증 후 로그인할 수 있습니다.',
                'email': member.email,
                'user': _user_response(member),
            }, status=status.HTTP_201_CREATED)
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

        if not member.email_verified:
            return Response({
                'error': '이메일 인증을 완료해 주세요. 가입 시 발송된 메일의 인증 링크를 클릭해 주세요.'
            }, status=status.HTTP_403_FORBIDDEN)

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
        return Response({
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'expires_in': tokens['expires_in'],
            'user': _user_response(member),
        }, status=status.HTTP_200_OK)


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
        err, send_verification = _apply_kakao_unverified_email(member, data)
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
        if send_verification:
            _send_profile_verification_email(member)
        return Response(_user_response(member), status=status.HTTP_200_OK)


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
        err, send_verification = _apply_kakao_unverified_email(member, data)
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
    Body의 refresh_token으로 새 액세스/리프레시 토큰 발급.
    frontend_www 로그인 유지(401 시 갱신 재시도)용.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = (request.data or {}).get('refresh_token') or ''
        if not refresh_token:
            return Response(
                {'error': 'refresh_token이 필요합니다.'},
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
        return Response({
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'expires_in': tokens['expires_in'],
            'user': _user_response(member),
        }, status=status.HTTP_200_OK)
