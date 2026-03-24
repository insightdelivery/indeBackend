"""
공개 Hero용 GET /api/events/
"""

from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import create_error_response, create_success_response

from .content_resolution import load_content
from .hero_payload import build_hero_item
from .models import DisplayEvent
from .s3_utils import presign_event_banner_image_url


class PublicDisplayEventListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        event_type = (request.query_params.get("eventTypeCode") or "").strip()
        if not event_type:
            return Response(
                create_error_response("eventTypeCode는 필수입니다.", "01"),
                status=400,
            )

        now = timezone.now()
        qs = (
            DisplayEvent.objects.filter(
                event_type_code=event_type,
                is_active=True,
            )
            .filter(Q(start_at__isnull=True) | Q(start_at__lte=now))
            .filter(Q(end_at__isnull=True) | Q(end_at__gte=now))
            .order_by("display_order", "id")
        )

        out = []
        for ev in qs:
            content = load_content(ev.content_type_code, ev.content_id)
            item = build_hero_item(ev, content)
            iu = item.get("imageUrl")
            if iu:
                item["imageUrl"] = presign_event_banner_image_url(iu)
            out.append(item)

        return Response(
            create_success_response(out, "display events"),
            status=200,
        )
