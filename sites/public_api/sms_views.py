"""
휴대폰 SMS 인증 API — `POST /auth/send-sms`, `POST /auth/verify-sms`.

- Aligo 발송: `aligo_client.send_sms` (phoneVerificationAligo.md §1, §3).
- 아이디 찾기는 `verify-sms` 요청 시 `purpose: "find_id"` 로 구분(회원가입 `signup`과 별도 행).
"""
import logging
import random
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from django.conf import settings

from sites.public_api.aligo_client import send_sms
from sites.public_api.models import PhoneSmsVerification, PublicMemberShip
from sites.public_api.phone_normalize import (
    is_valid_kr_mobile,
    normalize_phone_kr,
    phone_already_registered,
    phone_registered_to_other_member,
)
from sites.public_api.utils import get_token_from_request, verify_jwt_token

logger = logging.getLogger(__name__)

CODE_TTL_SEC = 10 * 60
RESEND_COOLDOWN_SEC = 30
MAX_VERIFY_ATTEMPTS = 5


class SendSmsVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw = (request.data.get('phone') or '').strip()
        norm = normalize_phone_kr(raw)
        if not is_valid_kr_mobile(norm):
            return Response(
                {'error': '올바른 휴대폰 번호를 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if phone_already_registered(norm):
            return Response(
                {'error': '이미 가입된 휴대폰 번호입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        latest = (
            PhoneSmsVerification.objects.filter(phone=norm, purpose=PhoneSmsVerification.PURPOSE_SIGNUP)
            .order_by('-created_at')
            .first()
        )
        if latest and (now - latest.last_sent_at).total_seconds() < RESEND_COOLDOWN_SEC:
            wait = int(RESEND_COOLDOWN_SEC - (now - latest.last_sent_at).total_seconds())
            return Response(
                {'error': f'{wait}초 후에 다시 인증번호를 요청할 수 있습니다.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        code = str(random.randint(100000, 999999))
        code_hash = make_password(code)
        expires_at = now + timedelta(seconds=CODE_TTL_SEC)
        row = PhoneSmsVerification.objects.create(
            phone=norm,
            code_hash=code_hash,
            expires_at=expires_at,
            verified=False,
            attempt_count=0,
            last_sent_at=now,
            purpose=PhoneSmsVerification.PURPOSE_SIGNUP,
        )

        service = getattr(settings, 'SMS_SERVICE_NAME', 'INDE')
        msg = f'[{service}] 인증번호는 {code} 입니다. (10분 이내 입력)'
        ok, detail = send_sms(norm, msg)
        if not ok:
            row.delete()
            return Response(
                {'error': detail},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if getattr(settings, 'SMS_SKIP_SEND', False):
            logger.warning('SMS_SKIP_SEND: phone=%s code=%s', norm, code)

        return Response(
            {
                'success': True,
                'message': '인증번호를 발송했습니다.',
                'expires_in': CODE_TTL_SEC,
            },
            status=status.HTTP_200_OK,
        )


class VerifySmsVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_phone = (request.data.get('phone') or '').strip()
        code = (request.data.get('code') or '').strip()
        norm = normalize_phone_kr(raw_phone)
        if not is_valid_kr_mobile(norm) or len(code) != 6 or not code.isdigit():
            return Response(
                {'error': '휴대폰 번호와 6자리 인증번호를 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        purpose = (request.data.get('purpose') or PhoneSmsVerification.PURPOSE_SIGNUP).strip()
        if purpose not in (
            PhoneSmsVerification.PURPOSE_SIGNUP,
            PhoneSmsVerification.PURPOSE_FIND_ID,
            PhoneSmsVerification.PURPOSE_PROFILE_PHONE,
        ):
            purpose = PhoneSmsVerification.PURPOSE_SIGNUP

        now = timezone.now()
        row = (
            PhoneSmsVerification.objects.filter(
                phone=norm,
                verified=False,
                expires_at__gt=now,
                purpose=purpose,
            )
            .order_by('-created_at')
            .first()
        )
        if not row:
            return Response(
                {'error': '유효한 인증 요청이 없거나 만료되었습니다. 인증번호를 다시 요청해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if row.attempt_count >= MAX_VERIFY_ATTEMPTS:
            return Response(
                {'error': '인증 시도 횟수를 초과했습니다. 인증번호를 다시 요청해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        row.attempt_count += 1
        if not check_password(code, row.code_hash):
            row.save(update_fields=['attempt_count'])
            return Response(
                {'error': '인증번호가 올바르지 않습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        row.verified = True
        row.verified_at = now
        row.save(update_fields=['verified', 'attempt_count', 'verified_at'])
        return Response(
            {'success': True, 'message': '휴대폰 인증이 완료되었습니다.'},
            status=status.HTTP_200_OK,
        )


class SendProfilePhoneSmsView(APIView):
    """
    로그인 사용자 회원정보 휴대폰 변경용 SMS — POST /auth/send-sms-profile-phone/
    (phoneVerificationAligo.md · wwwMypage_userInfo §5.2)
    """

    permission_classes = [AllowAny]

    def post(self, request):
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

        raw = (request.data.get('phone') or '').strip()
        norm = normalize_phone_kr(raw)
        if not is_valid_kr_mobile(norm):
            return Response(
                {'error': '올바른 휴대폰 번호를 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        current_norm = normalize_phone_kr(member.phone or '')
        if norm == current_norm:
            return Response(
                {'error': '현재와 다른 휴대폰 번호를 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if phone_registered_to_other_member(norm, member.member_sid):
            return Response(
                {'error': '이미 다른 계정에 등록된 번호입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        purpose = PhoneSmsVerification.PURPOSE_PROFILE_PHONE
        latest = (
            PhoneSmsVerification.objects.filter(phone=norm, purpose=purpose)
            .order_by('-created_at')
            .first()
        )
        if latest and (now - latest.last_sent_at).total_seconds() < RESEND_COOLDOWN_SEC:
            wait = int(RESEND_COOLDOWN_SEC - (now - latest.last_sent_at).total_seconds())
            return Response(
                {'error': f'{wait}초 후에 다시 인증번호를 요청할 수 있습니다.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        code = str(random.randint(100000, 999999))
        code_hash = make_password(code)
        expires_at = now + timedelta(seconds=CODE_TTL_SEC)
        PhoneSmsVerification.objects.create(
            phone=norm,
            code_hash=code_hash,
            expires_at=expires_at,
            verified=False,
            attempt_count=0,
            last_sent_at=now,
            purpose=purpose,
        )

        service = getattr(settings, 'SMS_SERVICE_NAME', 'INDE')
        msg = f'[{service}] 인증번호는 {code} 입니다. (10분 이내 입력)'
        ok, detail = send_sms(norm, msg)
        if not ok:
            last = (
                PhoneSmsVerification.objects.filter(phone=norm, purpose=purpose, verified=False)
                .order_by('-created_at')
                .first()
            )
            if last:
                last.delete()
            return Response({'error': detail}, status=status.HTTP_502_BAD_GATEWAY)

        if getattr(settings, 'SMS_SKIP_SEND', False):
            logger.warning('SMS_SKIP_SEND: profile_phone phone=%s code=%s', norm, code)

        return Response(
            {
                'success': True,
                'message': '인증번호를 발송했습니다.',
                'expires_in': CODE_TTL_SEC,
            },
            status=status.HTTP_200_OK,
        )
