"""
아이디 찾기·비밀번호 재설정 API.

- SMS는 모두 `aligo_client.send_sms` (phoneVerificationAligo.md).
- 상세 플로우: userIdPwFindPlan.md
"""
import logging
import random
import time
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.mail import send_email
from sites.public_api.account_recovery import (
    create_password_reset_jwt,
    new_password_reset_nonce,
    normalize_email,
    verify_password_reset_jwt,
)
from sites.public_api.aligo_client import send_sms
from sites.public_api.models import PhoneSmsVerification, PublicMemberShip
from sites.public_api.phone_normalize import is_valid_kr_mobile, normalize_phone_kr

logger = logging.getLogger(__name__)

CODE_TTL_SEC = 10 * 60
RESEND_COOLDOWN_SEC = 30
PW_RESET_CODE_TTL = 600
PW_RESET_NONCE_TTL = 600
MAX_CODE_ATTEMPTS = 5
PW_RESET_PUBLIC_MSG = '입력하신 이메일로 안내가 전송되었습니다.'
ERR_FIND_ID_NO_PHONE = '등록된 휴대폰 번호가 없습니다. 가입 시 입력한 번호인지 확인해 주세요.'
ERR_FIND_ID_SNS_ONLY = (
    '이 번호는 SNS(구글·네이버·카카오) 로그인으로 가입된 계정입니다. 해당 서비스를 통해 로그인해 주세요.'
)
ERR_PW_RESET_EMAIL_NOT_FOUND = (
    '등록되지 않은 이메일입니다. 가입 시 사용한 이메일인지 확인해 주세요.'
)
ERR_PW_RESET_EMAIL_SNS_ONLY = (
    '이 이메일은 SNS(구글·네이버·카카오) 로그인으로 가입된 계정입니다. 해당 서비스를 통해 로그인해 주세요.'
)
PW_RESET_PUBLIC_MSG_PHONE = '입력하신 휴대폰 번호로 안내가 전송되었습니다.'


def _local_member_by_phone(norm: str):
    qs = PublicMemberShip.objects.filter(
        is_active=True,
        joined_via='LOCAL',
        status=PublicMemberShip.STATUS_ACTIVE,
    ).only('member_sid', 'email', 'phone')
    for m in qs:
        if normalize_phone_kr(m.phone or '') == norm:
            return m
    return None


def _active_member_by_phone_any(norm: str):
    """활성·정상 회원 중 휴대폰 정규화 일치 (joined_via 무관, 아이디 찾기 사전 조회용)."""
    qs = PublicMemberShip.objects.filter(
        is_active=True,
        status=PublicMemberShip.STATUS_ACTIVE,
    ).only('member_sid', 'email', 'phone', 'joined_via')
    for m in qs:
        if normalize_phone_kr(m.phone or '') == norm:
            return m
    return None


def _rate_limit_pw_reset_send(email_norm: str) -> bool:
    """1분당 최대 3회 발송 허용. 초과 시 False."""
    bucket = int(time.time() // 60)
    k = f'pw_reset_rl:{email_norm}:{bucket}'
    n = cache.get(k) or 0
    if n >= 3:
        return False
    cache.set(k, n + 1, 120)
    return True


def _rate_limit_pw_reset_send_phone(phone_norm: str) -> bool:
    """휴대폰 경로 — 1분당 최대 3회 SMS 발송 허용."""
    bucket = int(time.time() // 60)
    k = f'pw_reset_rl_phone:{phone_norm}:{bucket}'
    n = cache.get(k) or 0
    if n >= 3:
        return False
    cache.set(k, n + 1, 120)
    return True


def _password_policy_ok(raw: str) -> bool:
    if len(raw) < 8:
        return False
    has_letter = any(c.isalpha() for c in raw)
    has_digit = any(c.isdigit() for c in raw)
    return has_letter and has_digit


class SendSmsFindIdView(APIView):
    """휴대폰 인증번호 발송 — 가입된 LOCAL 번호만 실제 발송 (아이디 찾기)."""

    permission_classes = [AllowAny]

    def post(self, request):
        raw = (request.data.get('phone') or '').strip()
        norm = normalize_phone_kr(raw)
        if not is_valid_kr_mobile(norm):
            return Response({'error': '올바른 휴대폰 번호를 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        any_member = _active_member_by_phone_any(norm)
        if not any_member:
            return Response({'error': ERR_FIND_ID_NO_PHONE}, status=status.HTTP_400_BAD_REQUEST)
        if any_member.joined_via != 'LOCAL':
            return Response({'error': ERR_FIND_ID_SNS_ONLY}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        latest = (
            PhoneSmsVerification.objects.filter(phone=norm, purpose=PhoneSmsVerification.PURPOSE_FIND_ID)
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
            purpose=PhoneSmsVerification.PURPOSE_FIND_ID,
        )

        service = getattr(settings, 'SMS_SERVICE_NAME', 'INDE')
        msg = f'[{service}] 인증번호는 {code} 입니다. (10분 이내 입력)'
        ok, detail = send_sms(norm, msg)
        if not ok:
            row.delete()
            return Response({'error': detail}, status=status.HTTP_502_BAD_GATEWAY)

        if getattr(settings, 'SMS_SKIP_SEND', False):
            logger.warning('SMS_SKIP_SEND find-id: phone=%s code=%s', norm, code)

        return Response(
            {'success': True, 'message': '인증번호를 발송했습니다.', 'expires_in': CODE_TTL_SEC},
            status=status.HTTP_200_OK,
        )


class FindIdView(APIView):
    """휴대폰 SMS 인증 완료 후 LOCAL 계정 이메일 반환."""

    permission_classes = [AllowAny]

    def post(self, request):
        raw_phone = (request.data.get('phone') or '').strip()
        norm = normalize_phone_kr(raw_phone)
        if not is_valid_kr_mobile(norm):
            return Response({'error': '올바른 휴대폰 번호를 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        if not PhoneSmsVerification.objects.filter(
            phone=norm, verified=True, purpose=PhoneSmsVerification.PURPOSE_FIND_ID
        ).exists():
            return Response(
                {'error': '휴대폰 인증을 완료한 뒤 다시 시도해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member = _local_member_by_phone(norm)
        if not member:
            return Response(
                {'error': '조건에 맞는 계정을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        PhoneSmsVerification.objects.filter(phone=norm, purpose=PhoneSmsVerification.PURPOSE_FIND_ID).delete()
        return Response({'email': member.email}, status=status.HTTP_200_OK)


class SendPasswordResetCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email_raw = (request.data.get('email') or '').strip()
        phone_raw = (request.data.get('phone') or '').strip()

        if email_raw and phone_raw:
            return Response(
                {'error': '이메일 또는 휴대폰 번호 중 하나만 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if phone_raw:
            return self._send_by_phone(phone_raw)

        email_norm = normalize_email(email_raw)
        if not email_norm or '@' not in email_norm:
            return Response(
                {'error': '올바른 이메일 형식을 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member_any = PublicMemberShip.objects.filter(
            email__iexact=email_norm,
            is_active=True,
            status=PublicMemberShip.STATUS_ACTIVE,
        ).first()
        if not member_any:
            return Response({'error': ERR_PW_RESET_EMAIL_NOT_FOUND}, status=status.HTTP_400_BAD_REQUEST)
        if member_any.joined_via != 'LOCAL':
            return Response({'error': ERR_PW_RESET_EMAIL_SNS_ONLY}, status=status.HTTP_400_BAD_REQUEST)

        member = member_any

        if not _rate_limit_pw_reset_send(email_norm):
            return Response({'message': PW_RESET_PUBLIC_MSG}, status=status.HTTP_200_OK)

        code = str(random.randint(100000, 999999))
        code_hash = make_password(code)
        cache_key = f'pw_reset:{email_norm}'
        cache.set(
            cache_key,
            {'code_hash': code_hash, 'attempts': 0},
            PW_RESET_CODE_TTL,
        )

        subject = '[인디] 비밀번호 재설정 인증 코드'
        body_text = (
            f'비밀번호 재설정을 요청하셨습니다.\n\n인증 코드: {code}\n\n'
            f'해당 코드는 10분간 유효하며 1회만 사용할 수 있습니다.\n'
            f'이 인증 코드는 절대 타인에게 공유하지 마세요.\n\n'
            f'본인이 요청하지 않았다면 이 메일을 무시하세요.'
        )
        body_html = f'<p>인증 코드: <strong>{code}</strong></p><p>10분 이내 입력, 1회 사용 가능.</p>'
        sent = send_email(member.email, subject, body_html, body_text)
        if not sent:
            cache.delete(cache_key)
            logger.warning('비밀번호 재설정 메일 발송 실패: %s', member.email)

        return Response({'message': PW_RESET_PUBLIC_MSG}, status=status.HTTP_200_OK)

    def _send_by_phone(self, phone_raw: str):
        """LOCAL 가입 번호에만 SMS 발송. 미등록·SNS는 명시 오류."""
        norm = normalize_phone_kr(phone_raw)
        if not is_valid_kr_mobile(norm):
            return Response(
                {'error': '휴대폰 번호를 올바르게 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member_any = _active_member_by_phone_any(norm)
        if not member_any:
            return Response({'error': ERR_FIND_ID_NO_PHONE}, status=status.HTTP_400_BAD_REQUEST)
        if member_any.joined_via != 'LOCAL':
            return Response({'error': ERR_FIND_ID_SNS_ONLY}, status=status.HTTP_400_BAD_REQUEST)

        cd_key = f'pw_reset_sms_cd:{norm}'
        if cache.get(cd_key):
            return Response(
                {'error': f'{RESEND_COOLDOWN_SEC}초 이내에 재요청할 수 없습니다.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if not _rate_limit_pw_reset_send_phone(norm):
            return Response({'message': PW_RESET_PUBLIC_MSG_PHONE}, status=status.HTTP_200_OK)

        code = str(random.randint(100000, 999999))
        code_hash = make_password(code)
        cache_key = f'pw_reset_phone:{norm}'
        cache.set(
            cache_key,
            {'code_hash': code_hash, 'attempts': 0},
            PW_RESET_CODE_TTL,
        )
        cache.set(cd_key, 1, RESEND_COOLDOWN_SEC)

        service = getattr(settings, 'SMS_SERVICE_NAME', 'INDE')
        msg = f'[{service}] 비밀번호 재설정 인증번호는 {code} 입니다. (10분 이내 입력)'
        ok, detail = send_sms(norm, msg)
        if not ok:
            cache.delete(cache_key)
            cache.delete(cd_key)
            return Response({'error': detail}, status=status.HTTP_502_BAD_GATEWAY)

        if getattr(settings, 'SMS_SKIP_SEND', False):
            logger.warning('SMS_SKIP_SEND pw-reset: phone=%s code=%s', norm, code)

        return Response({'message': PW_RESET_PUBLIC_MSG_PHONE}, status=status.HTTP_200_OK)


class VerifyPasswordResetCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email_norm = normalize_email((request.data.get('email') or '').strip())
        phone_raw = (request.data.get('phone') or '').strip()
        code = (request.data.get('code') or '').strip()

        if email_norm and phone_raw:
            return Response(
                {'error': '이메일 또는 휴대폰 번호 중 하나만 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not email_norm and not phone_raw:
            return Response(
                {'error': '이메일 또는 휴대폰 번호와 인증코드를 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(code) != 6 or not code.isdigit():
            return Response({'error': '6자리 인증코드를 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        phone_norm = ''
        if email_norm:
            cache_key = f'pw_reset:{email_norm}'
        else:
            phone_norm = normalize_phone_kr(phone_raw)
            if not is_valid_kr_mobile(phone_norm):
                return Response({'error': '올바른 휴대폰 번호를 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)
            cache_key = f'pw_reset_phone:{phone_norm}'

        data = cache.get(cache_key)
        if not data:
            return Response({'error': '인증코드가 만료되었거나 올바르지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        attempts = data.get('attempts', 0)
        if attempts >= MAX_CODE_ATTEMPTS:
            cache.delete(cache_key)
            return Response({'error': '인증 시도 횟수를 초과했습니다. 처음부터 다시 시도해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(code, data['code_hash']):
            data['attempts'] = attempts + 1
            cache.set(cache_key, data, PW_RESET_CODE_TTL)
            return Response({'error': '인증코드가 올바르지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if email_norm:
            member = (
                PublicMemberShip.objects.filter(
                    email__iexact=email_norm, joined_via='LOCAL', is_active=True
                )
                .exclude(status=PublicMemberShip.STATUS_WITHDRAWN)
                .first()
            )
        else:
            member = _local_member_by_phone(phone_norm)

        if not member:
            cache.delete(cache_key)
            return Response({'error': '계정을 찾을 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        cache.delete(cache_key)
        nonce = new_password_reset_nonce()
        nonce_key = f'pw_reset_nonce:{nonce}'
        cache.set(nonce_key, {'user_id': member.member_sid, 'used': False}, PW_RESET_NONCE_TTL)
        reset_token = create_password_reset_jwt(member.member_sid, nonce)
        return Response({'reset_token': reset_token}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        reset_token = (request.data.get('reset_token') or '').strip()
        new_pw = (request.data.get('password') or '').strip()
        payload = verify_password_reset_jwt(reset_token)
        if not payload:
            return Response({'error': '유효하지 않거나 만료된 재설정 토큰입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        nonce = payload.get('nonce')
        user_id = payload.get('user_id')
        if not nonce or not user_id:
            return Response({'error': '유효하지 않은 토큰입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        nonce_key = f'pw_reset_nonce:{nonce}'
        nd = cache.get(nonce_key)
        if not nd or nd.get('used'):
            return Response({'error': '이미 사용된 재설정 요청입니다.'}, status=status.HTTP_403_FORBIDDEN)

        if str(nd.get('user_id')) != str(user_id):
            return Response({'error': '토큰이 일치하지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            member = PublicMemberShip.objects.get(member_sid=int(user_id))
        except (PublicMemberShip.DoesNotExist, ValueError):
            return Response({'error': '계정을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        if member.joined_via != 'LOCAL' or not member.is_active or member.status != PublicMemberShip.STATUS_ACTIVE:
            return Response({'error': '비밀번호를 변경할 수 없는 계정입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if member.password and check_password(new_pw, member.password):
            return Response({'error': '이전과 다른 비밀번호를 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        if not _password_policy_ok(new_pw):
            return Response(
                {'error': '비밀번호는 8자 이상이며 영문과 숫자를 포함해야 합니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member.set_password(new_pw)
        member.save()
        nd['used'] = True
        cache.set(nonce_key, nd, 60)

        return Response({'success': True, 'message': '비밀번호가 변경되었습니다. 다시 로그인해 주세요.'}, status=status.HTTP_200_OK)
