"""
공개 API 뷰 (PublicMemberShip 기반 일반 회원가입/로그인)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from core.models import AuditLog
from sites.public_api.models import PublicMemberShip
from sites.public_api.serializers import RegisterSerializer, LoginSerializer
from sites.public_api.utils import create_public_jwt_tokens, get_token_from_request, verify_jwt_token
from sites.public_api import email_verification


def _user_response(member):
    """PublicMemberShip -> API 응답 user 객체"""
    return {
        'id': member.member_sid,
        'email': member.email,
        'name': member.name,
        'nickname': member.nickname,
        'phone': member.phone,
        'profile_completed': member.profile_completed,
        'joined_via': member.joined_via,
        'is_staff': getattr(member, 'is_staff', False),
    }


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR', '')


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
        try:
            member = PublicMemberShip(
                email=data['email'],
                name=data['name'],
                nickname=data['nickname'],
                phone=data['phone'],
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
            member = PublicMemberShip.objects.get(email=email, joined_via='LOCAL', is_active=True)
        except PublicMemberShip.DoesNotExist:
            return Response({
                'error': '해당 회원 정보를 찾을 수 없습니다.',
            }, status=status.HTTP_404_NOT_FOUND)
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
            member = PublicMemberShip.objects.get(
                email=email, joined_via='LOCAL', is_active=True
            )
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
        return Response({'message': '프로필이 완료되었습니다.', 'user': _user_response(member)}, status=status.HTTP_200_OK)
