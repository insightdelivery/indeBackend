"""콘텐츠 랭킹 조회 API — content_ranking_cache 만 사용 (schedulerContentPlan.md)"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from core.utils import create_success_response, create_error_response
from sites.public_api.models import ContentRankingCache


def _weekly_cross_list():
    """WEEKLY_CROSS: content_type이 ARTICLE/VIDEO/SEMINAR 혼합."""
    d = timezone.localdate()
    qs = (
        ContentRankingCache.objects.filter(
            ranking_type=ContentRankingCache.RANKING_WEEKLY_CROSS,
            base_date=d,
        )
        .order_by('rank_order')
        .values('content_type', 'content_code', 'score', 'rank_order')
    )
    return [
        {
            'contentType': row['content_type'],
            'contentCode': row['content_code'],
            'score': row['score'],
            'rankOrder': row['rank_order'],
        }
        for row in qs
    ]


def _ranking_list(ranking_type: str, content_type: str = 'ARTICLE'):
    d = timezone.localdate()
    qs = (
        ContentRankingCache.objects.filter(
            ranking_type=ranking_type,
            content_type=content_type,
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
    """GET /api/library/ranking/share — 당일 SHARE(캐시). ?contentType=ARTICLE|VIDEO|SEMINAR (기본 ARTICLE)"""

    permission_classes = []

    def get(self, request):
        try:
            ct = (request.query_params.get('contentType') or 'ARTICLE').strip().upper()
            if ct not in ('ARTICLE', 'VIDEO', 'SEMINAR'):
                ct = 'ARTICLE'
            items = _ranking_list(ContentRankingCache.RANKING_SHARE, ct)
            return Response(
                create_success_response({'list': items}),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                create_error_response(f'랭킹 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LibraryRankingRecommendedView(APIView):
    """GET /api/library/ranking/recommended — 당일 RECOMMENDED 아티클(캐시, §D)"""

    permission_classes = []

    def get(self, request):
        try:
            items = _ranking_list(ContentRankingCache.RANKING_RECOMMENDED)
            return Response(
                create_success_response({'list': items}),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                create_error_response(f'랭킹 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LibraryRankingWeeklyCrossView(APIView):
    """GET /api/library/ranking/weekly — 당일 WEEKLY_CROSS(§E), 타입 혼합"""

    permission_classes = []

    def get(self, request):
        try:
            items = _weekly_cross_list()
            return Response(
                create_success_response({'list': items}),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                create_error_response(f'랭킹 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
