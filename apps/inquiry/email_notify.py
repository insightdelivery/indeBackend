"""
1:1 문의 답변 등록 시 회원에게 안내 메일 (core.mail.send_email)
열람 추적: HTML 메일에 1x1 픽셀 URL → public_api /api/inquiries/email-open/<token>
"""
import logging
import uuid
from html import escape

from django.conf import settings
from django.utils import timezone

from core.mail import send_email

from .models import Inquiry

logger = logging.getLogger(__name__)


def send_inquiry_answer_notification(inquiry: Inquiry) -> bool:
    """
    문의자 이메일로 답변 안내 메일 발송. 성공 시 answer_email_sent_at 기록.
    INQUIRY_EMAIL_TRACK_BASE_URL 이 비어 있으면 픽셀 없이 본문만 발송.
    """
    user = getattr(inquiry, "user", None)
    if not user:
        logger.warning("inquiry %s: user 없음, 메일 생략", inquiry.pk)
        return False
    to_email = (getattr(user, "email", None) or "").strip()
    if not to_email:
        logger.warning("inquiry %s: 회원 이메일 없음, 메일 생략", inquiry.pk)
        return False

    token = uuid.uuid4().hex
    inquiry.answer_email_track_token = token
    inquiry.save(update_fields=["answer_email_track_token"])

    base = (getattr(settings, "INQUIRY_EMAIL_TRACK_BASE_URL", None) or "").strip().rstrip("/")
    pixel_html = ""
    if base:
        pixel_url = f"{base}/api/inquiries/email-open/{token}"
        pixel_html = (
            f'<img src="{escape(pixel_url)}" alt="" width="1" height="1" '
            'style="display:none" />'
        )

    subject = f"[InDe] 1:1 문의 답변이 등록되었습니다"
    plain = (inquiry.answer or "").strip()
    name = escape((getattr(user, "name", None) or "").strip() or "회원")
    safe_answer = escape(inquiry.answer or "").replace("\n", "<br/>")
    body_html = f"""<p>안녕하세요, {name}님,</p>
<p>문의하신 내용에 대한 답변입니다.</p>
<div style="margin:16px 0;padding:12px;border:1px solid #e5e7eb;border-radius:8px;">{safe_answer}</div>
<p style="font-size:12px;color:#6b7280;">문의 제목: {escape(inquiry.title[:200])}</p>
{pixel_html}"""

    ok = send_email(to_email, subject, body_html, body_text=plain)
    if ok:
        inquiry.answer_email_sent_at = timezone.now()
        inquiry.save(update_fields=["answer_email_sent_at"])
    return ok
