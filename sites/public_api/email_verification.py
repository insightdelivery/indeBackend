"""
이메일 인증 처리 (별도 프로그램)
- 인증 토큰 생성/검증 (JWT)
- 인증 메일 발송
"""
import jwt
from datetime import datetime, timedelta
from django.conf import settings

from core.mail import send_email


VERIFICATION_TOKEN_EXPIRE_HOURS = 24
VERIFICATION_CLAIM_EMAIL = 'email'
VERIFICATION_CLAIM_EXP = 'exp'
VERIFICATION_CLAIM_PURPOSE = 'email_verify'


def create_verification_token(email: str) -> str:
    """이메일 인증용 JWT 토큰 생성 (24시간 유효)."""
    secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    payload = {
        VERIFICATION_CLAIM_EMAIL: email,
        VERIFICATION_CLAIM_EXP: datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS),
        VERIFICATION_CLAIM_PURPOSE: 'public_email_verify',
    }
    return jwt.encode(payload, secret, algorithm='HS256')


def verify_verification_token(token: str) -> str | None:
    """토큰 검증 후 이메일 반환. 실패 시 None."""
    if not token:
        return None
    secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        if payload.get(VERIFICATION_CLAIM_PURPOSE) != 'public_email_verify':
            return None
        return payload.get(VERIFICATION_CLAIM_EMAIL)
    except Exception:
        return None


def get_verification_link(token: str) -> str:
    """인증 클릭 URL (프론트 verify 페이지). settings.PUBLIC_VERIFY_BASE_URL 사용."""
    base = getattr(settings, 'PUBLIC_VERIFY_BASE_URL', '').rstrip('/')
    if not base:
        base = 'http://localhost:3000'  # 개발 기본
    return f"{base}/auth/verify-email?token={token}"


def send_verification_email(to_email: str, verify_url: str) -> bool:
    """인증 메일 발송."""
    subject = '[인디] 이메일 인증을 완료해 주세요'
    body_text = f'아래 링크를 클릭하면 이메일 인증이 완료됩니다.\n\n{verify_url}\n\n24시간 이내에 클릭해 주세요.'
    body_html = f'''
    <p>안녕하세요, 인디입니다.</p>
    <p>회원가입을 완료하려면 아래 버튼을 클릭해 이메일 인증을 완료해 주세요.</p>
    <p><a href="{verify_url}" style="display:inline-block; padding:12px 24px; background:#000; color:#fff; text-decoration:none; border-radius:6px;">이메일 인증하기</a></p>
    <p>또는 아래 링크를 복사해 브라우저에 붙여넣기 하세요.</p>
    <p><a href="{verify_url}">{verify_url}</a></p>
    <p>본인이 요청한 것이 아니라면 이 메일을 무시해 주세요. (24시간 후 링크는 만료됩니다.)</p>
    '''
    return send_email(to_email, subject, body_html, body_text)
