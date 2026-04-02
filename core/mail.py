"""
메일 발송 라이브러리 (Gmail SMTP)
- env: GMAIL_SENDER(발신 이메일), GMAIL_APP_PASSWORD 또는 GOOGLE_API_KEY(Gmail 앱 비밀번호 16자)
- 참고: Gmail SMTP는 'Google API 키(AIza...)'가 아니라 '앱 비밀번호'가 필요합니다.
  Google 계정 → 보안 → 2단계 인증 → 앱 비밀번호 에서 생성.
- 관리자 배치 발송: `from_email`로 표시 주소를 주면 From 헤더에 반영(해당 주소는 Gmail「다른 주소로 보내기」에 등록된 경우에만 안정적).
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    body_text: str | None = None,
    *,
    from_email: str | None = None,
    from_display_name: str | None = None,
    reply_to: str | None = None,
) -> bool:
    """
    Gmail SMTP로 이메일 발송.
    env: GMAIL_SENDER, GMAIL_APP_PASSWORD(우선) 또는 GOOGLE_API_KEY(앱 비밀번호)
    """
    sender = (os.getenv('GMAIL_SENDER') or '').strip()
    password = (os.getenv('GMAIL_APP_PASSWORD') or os.getenv('GOOGLE_API_KEY') or '').strip()

    if not sender:
        logger.warning('메일 발송 건너뜀: GMAIL_SENDER가 설정되지 않았습니다.')
        return False
    if not password:
        logger.warning('메일 발송 건너뜀: GMAIL_APP_PASSWORD 또는 GOOGLE_API_KEY가 설정되지 않았습니다.')
        return False
    if password.startswith('AIza'):
        logger.warning(
            '메일 발송 건너뜀: GOOGLE_API_KEY에 Google API 키가 설정되어 있습니다. '
            'Gmail 발송에는 Google 계정 → 보안 → 앱 비밀번호 로 생성한 16자 앱 비밀번호를 사용해야 합니다.'
        )
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['To'] = to_email

    from_addr = (from_email or '').strip()
    if from_addr:
        if from_display_name and from_display_name.strip():
            msg['From'] = formataddr((from_display_name.strip(), from_addr))
        else:
            msg['From'] = from_addr
        rt = (reply_to or from_addr).strip()
        if rt:
            msg['Reply-To'] = rt
    else:
        msg['From'] = sender

    if body_text:
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
    msg.attach(MIMEText(body_html, 'html', 'utf-8'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, to_email, msg.as_string())
        logger.info('메일 발송 성공: to=%s', to_email)
        return True
    except Exception as e:
        logger.exception('메일 발송 실패: to=%s, error=%s', to_email, e)
        return False
