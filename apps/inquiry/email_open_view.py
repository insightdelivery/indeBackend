"""
GET /api/inquiries/email-open/<token> — 메일 열람 추적용 1x1 GIF (인증 없음)
"""
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .models import Inquiry

# 최소 GIF 1x1 투명
_GIF_1X1 = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)


@require_GET
def inquiry_email_open(request, token: str):
    if token and len(token) <= 64:
        try:
            q = Inquiry.objects.filter(answer_email_track_token=token).first()
            if q is not None and q.answer_email_opened_at is None:
                q.answer_email_opened_at = timezone.now()
                q.save(update_fields=["answer_email_opened_at"])
        except Exception:
            pass
    return HttpResponse(_GIF_1X1, content_type="image/gif")
