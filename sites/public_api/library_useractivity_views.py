"""
라이브러리 사용자 활동 로그 API (userPublicActiviteLog.md)
- 조회/별점/북마크 기록 및 마이페이지 목록 조회
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Avg
from django.utils import timezone

from core.utils import create_success_response, create_error_response
from sites.public_api.models import PublicMemberShip, PublicUserActivityLog
from sites.public_api.utils import get_token_from_request, verify_jwt_token


def _get_member(request):
    """JWT에서 회원 조회. 실패 시 None."""
    token = get_token_from_request(request)
    payload = verify_jwt_token(token, token_type='access') if token else None
    if not payload:
        return None
    user_id = payload.get('user_id')
    try:
        return PublicMemberShip.objects.get(member_sid=int(user_id), is_active=True)
    except (PublicMemberShip.DoesNotExist, ValueError, TypeError):
        return None


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or ''


def _log_item_to_dict(log):
    """PublicUserActivityLog -> API 응답 항목."""
    return {
        'publicUserActivityLogId': log.public_user_activity_log_id,
        'contentType': log.content_type,
        'contentCode': log.content_code,
        'regDateTime': log.reg_date_time.isoformat() if log.reg_date_time else None,
        'ratingValue': log.rating_value,
        'title': getattr(log, 'title', None),
        'thumbnail': getattr(log, 'thumbnail', None),
        'category': getattr(log, 'category', None),
    }


CONTENT_TYPES = {'ARTICLE', 'VIDEO', 'SEMINAR'}
ACTIVITY_VIEW = 'VIEW'
ACTIVITY_RATING = 'RATING'
ACTIVITY_BOOKMARK = 'BOOKMARK'


class LibraryUserActivityView(APIView):
    """POST /api/library/useractivity/view - 콘텐츠 조회 기록"""
    permission_classes = []

    def post(self, request):
        member = _get_member(request)
        if not member:
            return Response(
                create_error_response('인증이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        data = request.data or {}
        content_type = (data.get('contentType') or '').strip().upper()
        content_code = (data.get('contentCode') or '').strip()
        if content_type not in CONTENT_TYPES or not content_code:
            return Response(
                create_error_response('contentType, contentCode가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        ip = _get_client_ip(request)
        ua = (request.META.get('HTTP_USER_AGENT') or '')[:500]
        now = timezone.now()
        log, created = PublicUserActivityLog.objects.update_or_create(
            user=member,
            content_type=content_type,
            content_code=content_code,
            activity_type=ACTIVITY_VIEW,
            defaults={'ip_address': ip, 'user_agent': ua, 'reg_date_time': now},
        )
        return Response(
            create_success_response({'result': 'ok'}),
            status=status.HTTP_200_OK,
        )


class LibraryUserActivityRating(APIView):
    """POST /api/library/useractivity/rating - 별점 등록 (기존 삭제 후 재등록)"""
    permission_classes = []

    def post(self, request):
        member = _get_member(request)
        if not member:
            return Response(
                create_error_response('인증이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        data = request.data or {}
        content_type = (data.get('contentType') or '').strip().upper()
        content_code = (data.get('contentCode') or '').strip()
        rating = data.get('rating')
        if content_type not in CONTENT_TYPES or not content_code:
            return Response(
                create_error_response('contentType, contentCode가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            rating = int(rating) if rating is not None else None
        except (TypeError, ValueError):
            rating = None
        if rating is None or rating < 1 or rating > 5:
            return Response(
                create_error_response('rating은 1~5 사이 정수여야 합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        PublicUserActivityLog.objects.filter(
            user=member,
            content_type=content_type,
            content_code=content_code,
            activity_type=ACTIVITY_RATING,
        ).delete()
        PublicUserActivityLog.objects.create(
            user=member,
            content_type=content_type,
            content_code=content_code,
            activity_type=ACTIVITY_RATING,
            rating_value=rating,
        )
        return Response(
            create_success_response({'result': 'ok'}),
            status=status.HTTP_200_OK,
        )


class LibraryUserActivityBookmark(APIView):
    """POST: 북마크 추가, DELETE: 북마크 취소"""
    permission_classes = []

    def post(self, request):
        member = _get_member(request)
        if not member:
            return Response(
                create_error_response('인증이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        data = request.data or {}
        content_type = (data.get('contentType') or '').strip().upper()
        content_code = (data.get('contentCode') or '').strip()
        if content_type not in CONTENT_TYPES or not content_code:
            return Response(
                create_error_response('contentType, contentCode가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        _, created = PublicUserActivityLog.objects.get_or_create(
            user=member,
            content_type=content_type,
            content_code=content_code,
            activity_type=ACTIVITY_BOOKMARK,
        )
        return Response(
            create_success_response({'result': 'ok'}),
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        member = _get_member(request)
        if not member:
            return Response(
                create_error_response('인증이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        data = request.data or request.query_params or {}
        content_type = (data.get('contentType') or '').strip().upper()
        content_code = (data.get('contentCode') or '').strip()
        if content_type not in CONTENT_TYPES or not content_code:
            return Response(
                create_error_response('contentType, contentCode가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        deleted, _ = PublicUserActivityLog.objects.filter(
            user=member,
            content_type=content_type,
            content_code=content_code,
            activity_type=ACTIVITY_BOOKMARK,
        ).delete()
        return Response(
            create_success_response({'result': 'ok'}),
            status=status.HTTP_200_OK,
        )


class LibraryStatsViewCount(APIView):
    """GET /api/library/stats/view-count - 콘텐츠별 조회수"""
    permission_classes = []

    def get(self, request):
        content_type = (request.query_params.get('contentType') or '').strip().upper()
        content_code = (request.query_params.get('contentCode') or '').strip()
        if content_type not in CONTENT_TYPES or not content_code:
            return Response(
                create_error_response('contentType, contentCode 쿼리가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        count = PublicUserActivityLog.objects.filter(
            content_type=content_type,
            content_code=content_code,
            activity_type=ACTIVITY_VIEW,
        ).count()
        return Response(
            create_success_response({'count': count}),
            status=status.HTTP_200_OK,
        )


class LibraryStatsRating(APIView):
    """GET /api/library/stats/rating - 콘텐츠별 평균 별점"""
    permission_classes = []

    def get(self, request):
        content_type = (request.query_params.get('contentType') or '').strip().upper()
        content_code = (request.query_params.get('contentCode') or '').strip()
        if content_type not in CONTENT_TYPES or not content_code:
            return Response(
                create_error_response('contentType, contentCode 쿼리가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        agg = PublicUserActivityLog.objects.filter(
            content_type=content_type,
            content_code=content_code,
            activity_type=ACTIVITY_RATING,
            rating_value__isnull=False,
        ).aggregate(rating=Avg('rating_value'), ratingCount=Count('public_user_activity_log_id'))
        rating = float(agg['rating']) if agg['rating'] is not None else None
        rating_count = agg['ratingCount'] or 0
        return Response(
            create_success_response({'rating': rating, 'ratingCount': rating_count}),
            status=status.HTTP_200_OK,
        )


class LibraryStatsBookmark(APIView):
    """GET /api/library/stats/bookmark - 콘텐츠별 북마크 수"""
    permission_classes = []

    def get(self, request):
        content_type = (request.query_params.get('contentType') or '').strip().upper()
        content_code = (request.query_params.get('contentCode') or '').strip()
        if content_type not in CONTENT_TYPES or not content_code:
            return Response(
                create_error_response('contentType, contentCode 쿼리가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        count = PublicUserActivityLog.objects.filter(
            content_type=content_type,
            content_code=content_code,
            activity_type=ACTIVITY_BOOKMARK,
        ).count()
        return Response(
            create_success_response({'count': count}),
            status=status.HTTP_200_OK,
        )


class LibraryMeViews(APIView):
    """GET /api/library/useractivity/me/views - 마이페이지 라이브러리(최근 본) 목록"""
    permission_classes = []

    def get(self, request):
        member = _get_member(request)
        if not member:
            return Response(
                create_error_response('인증이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        page = max(1, int(request.query_params.get('page', 1)))
        page_size = min(max(1, int(request.query_params.get('page_size', request.query_params.get('pageSize', 10)))), 50)
        qs = PublicUserActivityLog.objects.filter(
            user=member,
            activity_type=ACTIVITY_VIEW,
        ).order_by('-reg_date_time')
        total = qs.count()
        start = (page - 1) * page_size
        items = list(qs[start : start + page_size])
        list_data = [_log_item_to_dict(log) for log in items]
        return Response(
            create_success_response({
                'list': list_data,
                'total': total,
                'page': page,
                'page_size': page_size,
            }),
            status=status.HTTP_200_OK,
        )


class LibraryMeBookmarks(APIView):
    """GET /api/library/useractivity/me/bookmarks - 마이페이지 북마크 목록"""
    permission_classes = []

    def get(self, request):
        member = _get_member(request)
        if not member:
            return Response(
                create_error_response('인증이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        page = max(1, int(request.query_params.get('page', 1)))
        page_size = min(max(1, int(request.query_params.get('page_size', request.query_params.get('pageSize', 10)))), 50)
        qs = PublicUserActivityLog.objects.filter(
            user=member,
            activity_type=ACTIVITY_BOOKMARK,
        ).order_by('-reg_date_time')
        total = qs.count()
        start = (page - 1) * page_size
        items = list(qs[start : start + page_size])
        list_data = [_log_item_to_dict(log) for log in items]
        return Response(
            create_success_response({
                'list': list_data,
                'total': total,
                'page': page,
                'page_size': page_size,
            }),
            status=status.HTTP_200_OK,
        )


class LibraryMeRatings(APIView):
    """GET /api/library/useractivity/me/ratings - 마이페이지 별점 모아보기 목록"""
    permission_classes = []

    def get(self, request):
        member = _get_member(request)
        if not member:
            return Response(
                create_error_response('인증이 필요합니다.', '01'),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        page = max(1, int(request.query_params.get('page', 1)))
        page_size = min(max(1, int(request.query_params.get('page_size', request.query_params.get('pageSize', 10)))), 50)
        sort = (request.query_params.get('sort') or 'regDateTime_desc').strip()
        qs = PublicUserActivityLog.objects.filter(
            user=member,
            activity_type=ACTIVITY_RATING,
        )
        if sort == 'rating_desc':
            qs = qs.order_by('-rating_value', '-reg_date_time')
        elif sort == 'rating_asc':
            qs = qs.order_by('rating_value', '-reg_date_time')
        else:
            qs = qs.order_by('-reg_date_time')
        total = qs.count()
        # 요약: 평균, 총 개수, 분포
        summary_qs = PublicUserActivityLog.objects.filter(
            user=member,
            activity_type=ACTIVITY_RATING,
            rating_value__isnull=False,
        )
        avg_rating = summary_qs.aggregate(avg=Avg('rating_value'))['avg']
        summary_count = summary_qs.count()
        distribution = {}
        for r in range(1, 6):
            distribution[str(r)] = summary_qs.filter(rating_value=r).count()
        summary = {
            'avgRating': round(float(avg_rating), 1) if avg_rating is not None else 0,
            'totalCount': summary_count,
            'distribution': distribution,
        }
        start = (page - 1) * page_size
        items = list(qs[start : start + page_size])
        list_data = [_log_item_to_dict(log) for log in items]
        return Response(
            create_success_response({
                'summary': summary,
                'list': list_data,
                'total': total,
                'page': page,
                'page_size': page_size,
            }),
            status=status.HTTP_200_OK,
        )
