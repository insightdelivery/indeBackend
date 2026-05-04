"""
공개 큐레이션 목록 — curationContentPlan.md §5, 메인 §10 카드 데이터
한 큐레이션(Curation)에 포함된 여러 CurationItem을 순서대로 노출.
"""
from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from core.utils import create_success_response
from sites.admin_api.curation.curation_resolve import build_public_card, resolve_curation_target
from sites.admin_api.curation.models import Curation


class PublicCurationListView(APIView):
    """GET /api/curation/list — 노출 조건을 만족하는 큐레이션별 카드 목록"""

    permission_classes = [AllowAny]

    def get(self, request):
        now = timezone.now()
        qs = Curation.objects.filter(is_active=True, is_exposed=True).filter(
            Q(exposure_start_datetime__isnull=True) | Q(exposure_start_datetime__lte=now),
            Q(exposure_end_datetime__isnull=True) | Q(exposure_end_datetime__gte=now),
        ).order_by('-reg_datetime')
        curations_out = []
        flat_items = []
        for c in qs.prefetch_related('items'):
            cards = []
            for item in c.items.order_by('sort_order', 'id'):
                resolved = resolve_curation_target(item.content_type, item.content_code)
                if not resolved:
                    continue
                card = build_public_card(item, resolved)
                cards.append(card)
                flat_items.append(card)
            curations_out.append(
                {
                    'curationId': c.id,
                    'name': c.name or '',
                    'items': cards,
                }
            )
        return Response(
            create_success_response(
                {'curations': curations_out, 'items': flat_items},
                'SUCCESS',
            ),
            status=status.HTTP_200_OK,
        )
