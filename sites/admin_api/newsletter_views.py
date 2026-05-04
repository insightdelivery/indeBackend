"""
관리자 뉴스레터 API (newsLetterModelPlan.md §4·§13·§14)
"""
from datetime import datetime, timedelta
from io import BytesIO

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.utils import create_error_response, create_success_response
from sites.admin_api.authentication import AdminJWTAuthentication
from sites.public_api.models import NewsletterSubscriber
from sites.public_api.newsletter_service import (
    get_combined_newsletter_list,
    merge_member_agreements_into_subscriber_ledger,
)


def _format_latest_agree_for_excel(raw) -> str:
    """엑셀 표시용: yyyy-mm-dd HH:MM (설정 타임존 기준, 기본 Asia/Seoul)."""
    if raw is None or raw == '':
        return ''
    if isinstance(raw, datetime):
        dt = raw
    else:
        s = str(raw).strip()
        if not s:
            return ''
        try:
            dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
        except ValueError:
            return s
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return timezone.localtime(dt).strftime('%Y-%m-%d %H:%M')


class NewsletterCombinedView(APIView):
    """GET /api/newsletter/combined — 실시간 통합 목록(§14)"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_combined_newsletter_list()
        return Response(create_success_response({'items': data}), status=status.HTTP_200_OK)


class NewsletterExportView(APIView):
    """GET /api/newsletter/export — 통합 결과만 엑셀(§13-4)"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = get_combined_newsletter_list()
        wb = Workbook()
        ws = wb.active
        ws.title = 'newsletter'
        ws.append(['이메일', '이름', '출처', '광고동의', '최신동의시각'])
        for r in rows:
            ws.append(
                [
                    r.get('email', ''),
                    r.get('name', ''),
                    r.get('source', ''),
                    'Y' if r.get('agree_marketing') else 'N',
                    _format_latest_agree_for_excel(r.get('latest_agree_at')),
                ]
            )
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        filename = (
            f"newsletter_combined_{timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
        )
        resp = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp


class NewsletterMergeMembersView(APIView):
    """POST /api/newsletter/merge-members — 회원 동의 → 원장 upsert(§13-6 병합)"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        stats = merge_member_agreements_into_subscriber_ledger()
        return Response(create_success_response(stats), status=status.HTTP_200_OK)


class NewsletterSubscribersListView(APIView):
    """GET /api/newsletter/subscribers — 원장 목록(검색·필터)"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = NewsletterSubscriber.objects.all().order_by('-create_at')
        search = (request.query_params.get('search') or '').strip()
        if search:
            q = q.filter(Q(email__icontains=search) | Q(name__icontains=search))
        st = (request.query_params.get('status') or '').strip().upper()
        if st in (NewsletterSubscriber.STATUS_SUBSCRIBED, NewsletterSubscriber.STATUS_UNSUBSCRIBED):
            q = q.filter(subscribe_status=st)
        df = (request.query_params.get('date_from') or '').strip()
        dt = (request.query_params.get('date_to') or '').strip()
        if df:
            try:
                d0 = timezone.make_aware(datetime.strptime(df, '%Y-%m-%d'))
                q = q.filter(create_at__gte=d0)
            except ValueError:
                pass
        if dt:
            try:
                d1 = timezone.make_aware(datetime.strptime(dt, '%Y-%m-%d'))
                end = d1 + timedelta(days=1)
                q = q.filter(create_at__lt=end)
            except ValueError:
                pass

        page = int(request.query_params.get('page') or 1)
        page_size = min(int(request.query_params.get('page_size') or 20), 100)
        if page < 1:
            page = 1
        total = q.count()
        start = (page - 1) * page_size
        items = []
        for o in q[start : start + page_size]:
            items.append(
                {
                    'subscriber_id': o.subscriber_id,
                    'email': o.email,
                    'name': o.name or '',
                    'subscribe_status': o.subscribe_status,
                    'signup_source': o.signup_source,
                    'member_id': o.member_id,
                    'agree_datetime': o.agree_datetime.isoformat() if o.agree_datetime else None,
                    'create_at': o.create_at.isoformat() if o.create_at else None,
                }
            )
        return Response(
            create_success_response({'list': items, 'total': total, 'page': page, 'page_size': page_size}),
            status=status.HTTP_200_OK,
        )


class NewsletterSubscriberUnsubscribeView(APIView):
    """POST /api/newsletter/subscribers/<id>/unsubscribe — 원장 구독 취소(상태만)"""

    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, subscriber_id):
        try:
            o = NewsletterSubscriber.objects.get(subscriber_id=subscriber_id)
        except NewsletterSubscriber.DoesNotExist:
            return Response(
                create_error_response('구독자를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        if o.subscribe_status == NewsletterSubscriber.STATUS_UNSUBSCRIBED:
            return Response(
                create_success_response(
                    {
                        'subscriber_id': o.subscriber_id,
                        'subscribe_status': o.subscribe_status,
                    },
                    '이미 구독 취소 상태입니다.',
                ),
                status=status.HTTP_200_OK,
            )
        now = timezone.now()
        o.subscribe_status = NewsletterSubscriber.STATUS_UNSUBSCRIBED
        o.unsubscribe_datetime = now
        o.save(update_fields=['subscribe_status', 'unsubscribe_datetime'])
        return Response(
            create_success_response(
                {
                    'subscriber_id': o.subscriber_id,
                    'subscribe_status': o.subscribe_status,
                    'unsubscribe_datetime': o.unsubscribe_datetime.isoformat() if o.unsubscribe_datetime else None,
                },
                '구독이 취소 처리되었습니다.',
            ),
            status=status.HTTP_200_OK,
        )


class NewsletterSubscriberDestroyView(APIView):
    """DELETE /api/newsletter/subscribers/<id> — 원장 행 삭제"""

    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, subscriber_id):
        try:
            o = NewsletterSubscriber.objects.get(subscriber_id=subscriber_id)
        except NewsletterSubscriber.DoesNotExist:
            return Response(
                create_error_response('구독자를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        o.delete()
        return Response(
            create_success_response({'subscriber_id': subscriber_id, 'deleted': True}, '삭제되었습니다.'),
            status=status.HTTP_200_OK,
        )
