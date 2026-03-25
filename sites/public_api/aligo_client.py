"""Aligo SMS 발송 (phoneVerificationAligo.md)."""
import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ALIGO_SEND_URL = 'https://apis.aligo.in/send/'


def aligo_configured() -> bool:
    return bool(
        getattr(settings, 'ALIGO_API_KEY', '')
        and getattr(settings, 'ALIGO_USER_ID', '')
        and getattr(settings, 'ALIGO_SENDER', '')
    )


def send_sms(receiver: str, message: str) -> tuple[bool, str]:
    """
    Aligo SMS 전송.
    Returns (ok, detail_message).
    """
    if getattr(settings, 'SMS_SKIP_SEND', False):
        logger.warning('SMS_SKIP_SEND=1: SMS 미발송 receiver=%s msg=%s', receiver, message[:80])
        return True, 'dev_skip'

    if not aligo_configured():
        return False, 'Aligo SMS 환경변수(ALIGO_API_KEY, ALIGO_USER_ID, ALIGO_SENDER)가 설정되지 않았습니다.'

    payload = {
        'key': settings.ALIGO_API_KEY,
        'user_id': settings.ALIGO_USER_ID,
        'sender': settings.ALIGO_SENDER,
        'receiver': receiver,
        'msg': message,
        'msg_type': 'SMS',
    }
    try:
        r = requests.post(ALIGO_SEND_URL, data=payload, timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.exception('Aligo HTTP 오류: %s', e)
        return False, '문자 발송 서버 연결에 실패했습니다.'

    try:
        body: dict[str, Any] = r.json()
    except ValueError:
        logger.error('Aligo 비JSON 응답: %s', r.text[:500])
        return False, '문자 발송 응답을 처리할 수 없습니다.'

    # result_code "1" = 성공 (Aligo 문서 기준)
    code = str(body.get('result_code', ''))
    if code == '1':
        return True, body.get('message', '성공')

    msg = body.get('message') or body.get('msg') or str(body)
    logger.warning('Aligo 실패 result_code=%s body=%s', code, body)
    return False, msg if isinstance(msg, str) else '문자 발송에 실패했습니다.'
