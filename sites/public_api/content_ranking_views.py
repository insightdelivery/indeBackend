"""콘텐츠 랭킹 조회 API — content_ranking_cache 만 사용 (schedulerContentPlan.md §9)"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from core.utils import create_success_response, create_error_response
from sites.public_api.models import ContentRankingCache


def _ranking_list(ranking_type: str):
    d = timezone.localdate()
    qs = (
        ContentRankingCache.objects.filter(
            ranking_type=ranking_type,
            content_type='ARTICLE',
            base_date=d,
        )
        .order_by('rank_order')
        .values('content_code', 'score', 'rank_order')
    )
    items = [
        {
            'contentCode': row['content_code'],
            'score': row['score'],
            'rankOrder': row['rank_order'],
        }
        for row in qs
    ]
    return items


class LibraryRankingHotView(APIView):
    """GET /api/library/ranking/hot — 당일 HOT 아티클(캐시)"""

    permission_classes = []

    def get(self, request):
        try:
            items = _ranking_list(ContentRankingCache.RANKING_HOT)
            return Response(
                create_success_response({'list': items}),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                create_error_response(f'랭킹 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LibraryRankingShareView(APIView):
    """GET /api/library/ranking/share — 당일 SHARE 아티클(캐시)"""

    permission_classes = []

    def get(self, request):
        try:
            items = _ranking_list(ContentRankingCache.RANKING_SHARE)
            return Response(
                create_success_response({'list': items}),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                create_error_response(f'랭킹 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
