"""
관리자용 PublicMemberShip CRUD API (AdminJWT) + 탈퇴/복구
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from datetime import datetime, time, timedelta

from django.utils import timezone
from django.db.models import Avg, Count, Max, Q

from core.models import AuditLog
from core.utils import create_success_response, create_error_response
from sites.admin_api.authentication import AdminJWTAuthentication
from sites.admin_api.menu_codes import MenuCodes
from sites.admin_api.permissions import MenuPermission
from sites.public_api.models import PublicMemberShip, PublicUserActivityLog, IndeUser
from sites.admin_api.articles.models import Article
from sites.admin_api.articles.utils import get_presigned_thumbnail_url as article_presigned_thumbnail
from sites.admin_api.content_publish_syscodes import STATUS_PUBLISHED
from sites.admin_api.video.models import Video
from sites.admin_api.video.utils import get_presigned_thumbnail_url as video_presigned_thumbnail
from apps.highlight.models import ArticleHighlight
from apps.content_question.models import ContentQuestionAnswer
from .serializers import (
    PublicMemberListSerializer,
    PublicMemberDetailSerializer,
    PublicMemberCreateUpdateSerializer,
)


class PublicMemberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 250


class AdminPublicMemberViewSet(viewsets.ModelViewSet):
    """관리자 공개 회원(PublicMemberShip) CRUD + 탈퇴/복구"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.PUBLIC_MEMBERS
    queryset = PublicMemberShip.objects.all()
    pagination_class = PublicMemberPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["email", "name", "nickname", "phone"]
    ordering_fields = ["member_sid", "email", "created_at", "last_login", "status"]
    ordering = ["-created_at"]

    ACTIVITY_VIEW = 'VIEW'
    ACTIVITY_RATING = 'RATING'
    ACTIVITY_BOOKMARK = 'BOOKMARK'
    CONTENT_TYPES = {'ARTICLE', 'VIDEO', 'SEMINAR'}

    def get_queryset(self):
        qs = super().get_queryset()
        request = self.request
        scope = (request.query_params.get("recipient_scope") or "").strip().lower()

        if scope == "marketing_agree":
            qs = qs.filter(
                newsletter_agree=True,
                status=PublicMemberShip.STATUS_ACTIVE,
            )
        elif scope == "all":
            pass
        elif scope == "join_date":
            jf = (request.query_params.get("join_date_from") or "").strip()
            jt = (request.query_params.get("join_date_to") or "").strip()
            if not jf and not jt:
                qs = qs.none()
            else:
                if jf:
                    try:
                        d_from = datetime.strptime(jf, "%Y-%m-%d").date()
                        start_dt = timezone.make_aware(datetime.combine(d_from, time.min))
                        qs = qs.filter(created_at__gte=start_dt)
                    except ValueError:
                        pass
                if jt:
                    try:
                        d_to = datetime.strptime(jt, "%Y-%m-%d").date()
                        end_dt = timezone.make_aware(datetime.combine(d_to, time.max))
                        qs = qs.filter(created_at__lte=end_dt)
                    except ValueError:
                        pass
        elif scope == "inactive_90":
            cutoff = timezone.now() - timedelta(days=90)
            qs = qs.filter(status=PublicMemberShip.STATUS_ACTIVE).filter(
                Q(last_login__isnull=True) | Q(last_login__lt=cutoff)
            )
        elif scope == "withdrawn":
            qs = qs.filter(status=PublicMemberShip.STATUS_WITHDRAWN)
        else:
            status_filter = request.query_params.get("status")
            if status_filter in (
                PublicMemberShip.STATUS_ACTIVE,
                PublicMemberShip.STATUS_WITHDRAWN,
                PublicMemberShip.STATUS_WITHDRAW_REQUEST,
            ):
                qs = qs.filter(status=status_filter)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PublicMemberListSerializer
        if self.action == "retrieve":
            return PublicMemberDetailSerializer
        return PublicMemberCreateUpdateSerializer

    def _get_client_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def _parse_page(self, request, default_size=10, max_size=50):
        try:
            page = int(request.query_params.get('page', 1) or 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.query_params.get('page_size', request.query_params.get('pageSize', default_size)) or default_size)
        except (TypeError, ValueError):
            page_size = default_size
        page = max(1, page)
        page_size = min(max(1, page_size), max_size)
        return page, page_size

    def _presign_article_thumb(self, url):
        if not url:
            return None
        try:
            return article_presigned_thumbnail(url, expires_in=3600) or url
        except Exception:
            return url

    def _presign_video_thumb(self, url):
        if not url:
            return None
        try:
            return video_presigned_thumbnail(url, expires_in=3600) or url
        except Exception:
            return url

    def _attach_content_master_to_logs(self, logs):
        if not logs:
            return []

        article_codes = list({str(l.content_code).strip() for l in logs if l.content_type == 'ARTICLE'})
        video_codes = list({str(l.content_code).strip() for l in logs if l.content_type == 'VIDEO'})
        seminar_codes = list({str(l.content_code).strip() for l in logs if l.content_type == 'SEMINAR'})

        article_ids = [int(x) for x in article_codes if x.isdigit()]
        article_map = {}
        if article_ids:
            for a in Article.objects.filter(id__in=article_ids, deletedAt__isnull=True).only('id', 'title', 'subtitle', 'thumbnail', 'category'):
                article_map[str(a.id)] = a

        vid_ints = []
        for x in video_codes + seminar_codes:
            if x.isdigit():
                vid_ints.append(int(x))
        vid_ints = list(set(vid_ints))
        video_map = {}
        seminar_map = {}
        if vid_ints:
            for v in Video.objects.filter(id__in=vid_ints, deletedAt__isnull=True).only('id', 'contentType', 'title', 'subtitle', 'thumbnail', 'category'):
                key = str(v.id)
                if v.contentType == 'video':
                    video_map[key] = v
                elif v.contentType == 'seminar':
                    seminar_map[key] = v

        out = []
        for log in logs:
            code = str(log.content_code).strip()
            ct = log.content_type
            row = {
                'publicUserActivityLogId': log.public_user_activity_log_id,
                'contentType': ct,
                'contentCode': log.content_code,
                'regDateTime': log.reg_date_time.isoformat() if log.reg_date_time else None,
                'ratingValue': log.rating_value,
                'title': None,
                'subtitle': None,
                'thumbnail': None,
                'category': None,
                'contentMissing': False,
            }
            if ct == 'ARTICLE':
                art = article_map.get(code)
                if art:
                    row['title'] = art.title
                    row['subtitle'] = (art.subtitle or '').strip() or None
                    row['thumbnail'] = self._presign_article_thumb(art.thumbnail)
                    row['category'] = (art.category or '').strip() or None
                else:
                    row['title'] = '삭제된 콘텐츠입니다'
                    row['contentMissing'] = True
            elif ct == 'VIDEO':
                vid = video_map.get(code)
                if vid:
                    row['title'] = vid.title
                    row['subtitle'] = (vid.subtitle or '').strip() or None
                    row['thumbnail'] = self._presign_video_thumb(vid.thumbnail)
                    row['category'] = (vid.category or '').strip() or None
                else:
                    row['title'] = '삭제된 콘텐츠입니다'
                    row['contentMissing'] = True
            elif ct == 'SEMINAR':
                sem = seminar_map.get(code)
                if sem:
                    row['title'] = sem.title
                    row['subtitle'] = (sem.subtitle or '').strip() or None
                    row['thumbnail'] = self._presign_video_thumb(sem.thumbnail)
                    row['category'] = (sem.category or '').strip() or None
                else:
                    row['title'] = '삭제된 콘텐츠입니다'
                    row['contentMissing'] = True
            out.append(row)
        return out

    def _content_url_for_www(self, content_type, content_id):
        if content_type == 'ARTICLE':
            return f'/article/detail?id={content_id}'
        if content_type == 'VIDEO':
            return f'/video/detail?id={content_id}'
        if content_type == 'SEMINAR':
            return f'/seminar/detail?id={content_id}'
        return '#'

    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        """관리자 탈퇴 처리: status=WITHDRAWN, is_active=False (Soft Delete)"""
        member = self.get_object()
        if member.status == PublicMemberShip.STATUS_WITHDRAWN:
            return Response(
                {"detail": "이미 탈퇴 처리된 회원입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = request.data.get("reason") or ""
        detail_reason = request.data.get("detail_reason") or ""
        member.status = PublicMemberShip.STATUS_WITHDRAWN
        member.is_active = False
        member.withdraw_completed_at = timezone.now()
        member.withdraw_reason = reason or member.withdraw_reason
        member.withdraw_detail_reason = detail_reason or member.withdraw_detail_reason
        member.withdraw_ip = self._get_client_ip(request)
        member.withdraw_user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:500]
        member.save(update_fields=[
            "status", "is_active", "withdraw_completed_at",
            "withdraw_reason", "withdraw_detail_reason",
            "withdraw_ip", "withdraw_user_agent", "updated_at",
        ])
        AuditLog.objects.create(
            user_id=str(request.user.memberShipSid) if getattr(request.user, "memberShipSid", None) else "admin",
            site_slug="admin_api",
            action="update",
            resource="publicMemberShip",
            resource_id=str(member.member_sid),
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            details={"action": "withdraw", "member_sid": member.member_sid},
        )
        return Response(
            {"detail": "탈퇴 처리되었습니다.", "member_sid": member.member_sid},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """탈퇴 회원 정상 복구: status=ACTIVE, is_active=True, 탈퇴 필드 초기화"""
        member = self.get_object()
        if member.status != PublicMemberShip.STATUS_WITHDRAWN:
            return Response(
                {"detail": "탈퇴된 회원만 복구할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        member.status = PublicMemberShip.STATUS_ACTIVE
        member.is_active = True
        member.withdraw_reason = None
        member.withdraw_detail_reason = None
        member.withdraw_requested_at = None
        member.withdraw_completed_at = None
        member.withdraw_ip = None
        member.withdraw_user_agent = None
        member.save(update_fields=[
            "status", "is_active",
            "withdraw_reason", "withdraw_detail_reason",
            "withdraw_requested_at", "withdraw_completed_at",
            "withdraw_ip", "withdraw_user_agent", "updated_at",
        ])
        AuditLog.objects.create(
            user_id=str(request.user.memberShipSid) if getattr(request.user, "memberShipSid", None) else "admin",
            site_slug="admin_api",
            action="update",
            resource="publicMemberShip",
            resource_id=str(member.member_sid),
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            details={"action": "withdraw_restore", "member_sid": member.member_sid},
        )
        return Response(
            {"detail": "정상 회원으로 복구되었습니다.", "member_sid": member.member_sid},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="check-email")
    def check_email(self, request, pk=None):
        member = self.get_object()
        email = (request.query_params.get('email') or '').strip().lower()
        if not email:
            return Response(
                create_error_response('email 쿼리가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )

        duplicate_exists = PublicMemberShip.objects.filter(email__iexact=email).exclude(member_sid=member.member_sid).exists()
        return Response(
            create_success_response(
                {
                    'email': email,
                    'isDuplicate': duplicate_exists,
                    'memberSid': member.member_sid,
                }
            ),
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="activity/views")
    def activity_views(self, request, pk=None):
        member = self.get_object()
        page, page_size = self._parse_page(request, default_size=9)

        grouped = (
            PublicUserActivityLog.objects.filter(user_id=member.pk, activity_type=self.ACTIVITY_VIEW)
            .values('content_type', 'content_code')
            .annotate(max_time=Max('reg_date_time'))
            .order_by('-max_time')
        )
        total = grouped.count()
        total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1
        if total > 0 and page > total_pages:
            page = total_pages
        if total == 0:
            page = 1

        start = (page - 1) * page_size
        page_slice = list(grouped[start : start + page_size])

        logs = []
        for g in page_slice:
            ct = g['content_type']
            cc = str(g['content_code']).strip()
            log = (
                PublicUserActivityLog.objects.filter(
                    user_id=member.pk,
                    activity_type=self.ACTIVITY_VIEW,
                    content_type=ct,
                    content_code=cc,
                )
                .order_by('-reg_date_time', '-public_user_activity_log_id')
                .first()
            )
            if log:
                logs.append(log)

        list_data = self._attach_content_master_to_logs(logs)
        return Response(
            create_success_response(
                {'list': list_data, 'total': total, 'page': page, 'page_size': page_size}
            ),
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="activity/bookmarks")
    def activity_bookmarks(self, request, pk=None):
        member = self.get_object()
        page, page_size = self._parse_page(request, default_size=9)
        qs = PublicUserActivityLog.objects.filter(
            user_id=member.pk,
            activity_type=self.ACTIVITY_BOOKMARK,
        ).order_by('-reg_date_time')
        total = qs.count()
        start = (page - 1) * page_size
        items = list(qs[start : start + page_size])
        list_data = self._attach_content_master_to_logs(items)
        return Response(
            create_success_response(
                {'list': list_data, 'total': total, 'page': page, 'page_size': page_size}
            ),
            status=status.HTTP_200_OK,
        )

    @activity_bookmarks.mapping.delete
    def activity_bookmarks_delete(self, request, pk=None):
        member = self.get_object()
        data = request.data or request.query_params or {}
        content_type = (data.get('contentType') or '').strip().upper()
        content_code = (data.get('contentCode') or '').strip()
        if content_type not in self.CONTENT_TYPES or not content_code:
            return Response(
                create_error_response('contentType, contentCode가 필요합니다.'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        PublicUserActivityLog.objects.filter(
            user_id=member.pk,
            content_type=content_type,
            content_code=content_code,
            activity_type=self.ACTIVITY_BOOKMARK,
        ).delete()
        return Response(create_success_response({'result': 'ok'}), status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="activity/ratings")
    def activity_ratings(self, request, pk=None):
        member = self.get_object()
        page, page_size = self._parse_page(request, default_size=7)
        sort = (request.query_params.get('sort') or 'regDateTime_desc').strip()
        qs = PublicUserActivityLog.objects.filter(
            user_id=member.pk,
            activity_type=self.ACTIVITY_RATING,
        )
        if sort == 'rating_desc':
            qs = qs.order_by('-rating_value', '-reg_date_time')
        elif sort == 'rating_asc':
            qs = qs.order_by('rating_value', '-reg_date_time')
        else:
            qs = qs.order_by('-reg_date_time')
        total = qs.count()

        summary_qs = PublicUserActivityLog.objects.filter(
            user_id=member.pk,
            activity_type=self.ACTIVITY_RATING,
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
        list_data = self._attach_content_master_to_logs(items)
        return Response(
            create_success_response(
                {'summary': summary, 'list': list_data, 'total': total, 'page': page, 'page_size': page_size}
            ),
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="highlights")
    def highlights(self, request, pk=None):
        member = self.get_object()
        view = (request.query_params.get('view') or 'date').strip()
        page, page_size = self._parse_page(request, default_size=9)

        try:
            inde_user = IndeUser.objects.get(email=member.email, is_active=True)
        except IndeUser.DoesNotExist:
            return Response(
                create_success_response({'list': [], 'total': 0, 'page': 1, 'page_size': page_size}),
                status=status.HTTP_200_OK,
            )

        rows = (
            ArticleHighlight.objects.filter(user=inde_user)
            .select_related('article')
            .order_by('highlight_group_id', 'id')
        )
        by_gid = {}
        for row in rows:
            by_gid.setdefault(row.highlight_group_id, []).append(row)

        groups = []
        for gid, group_rows in by_gid.items():
            max_created = max(r.created_at for r in group_rows)
            rep_row = max(group_rows, key=lambda r: len((r.highlight_text or '')))
            article = rep_row.article
            article_id = article.id if article else rep_row.article_id
            title = '삭제된 콘텐츠입니다'
            thumb = None
            if article and getattr(article, 'deletedAt', None) is None and getattr(article, 'status', None) != 'deleted':
                title = article.title or ''
                thumb = self._presign_article_thumb((article.thumbnail or '').strip() or None)
            groups.append(
                {
                    'highlightGroupId': gid,
                    'articleId': article_id,
                    'highlightText': rep_row.highlight_text or '',
                    'articleTitle': title,
                    'thumbnail': thumb,
                    'createdAt': max_created.isoformat(),
                    '_sort': max_created,
                }
            )

        groups.sort(key=lambda x: x['_sort'], reverse=True)

        if view == 'article':
            grouped_items = {}
            for g in groups:
                grouped_items.setdefault(str(g['articleId']), []).append(g)
            flat = []
            for _, arr in grouped_items.items():
                arr.sort(key=lambda x: x['_sort'], reverse=True)
                flat.extend(arr)
        else:
            flat = groups

        total = len(flat)
        start = (page - 1) * page_size
        page_items = flat[start : start + page_size]
        list_data = [
            {
                'highlightGroupId': item['highlightGroupId'],
                'articleId': item['articleId'],
                'highlightText': item['highlightText'],
                'articleTitle': item['articleTitle'],
                'thumbnail': item['thumbnail'],
                'createdAt': item['createdAt'],
            }
            for item in page_items
        ]
        return Response(
            create_success_response({'list': list_data, 'total': total, 'page': page, 'page_size': page_size}),
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path=r"highlights/(?P<highlight_group_id>\d+)")
    def highlights_delete(self, request, pk=None, highlight_group_id=None):
        member = self.get_object()
        try:
            inde_user = IndeUser.objects.get(email=member.email, is_active=True)
        except IndeUser.DoesNotExist:
            return Response(
                create_error_response('해당 회원의 하이라이트 계정을 찾을 수 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
            )
        deleted, _ = ArticleHighlight.objects.filter(
            user=inde_user,
            highlight_group_id=int(highlight_group_id),
        ).delete()
        if deleted == 0:
            return Response(
                create_error_response('하이라이트 그룹을 찾을 수 없습니다.', '04'),
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(create_success_response({'result': 'ok'}), status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="applied-questions")
    def applied_questions(self, request, pk=None):
        member = self.get_object()
        page, page_size = self._parse_page(request, default_size=9)
        user_id = member.member_sid

        grouped = (
            ContentQuestionAnswer.objects.filter(user_id=user_id)
            .values('content_type', 'content_id')
            .annotate(answer_count=Count('answer_id'), last_answered_at=Max('created_at'))
            .order_by('-last_answered_at')
        )
        total = grouped.count()
        total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1
        if total > 0 and page > total_pages:
            page = total_pages
        if total == 0:
            page = 1

        start = (page - 1) * page_size
        page_slice = list(grouped[start : start + page_size])

        article_ids = [r['content_id'] for r in page_slice if r['content_type'] == 'ARTICLE']
        video_ids = [r['content_id'] for r in page_slice if r['content_type'] == 'VIDEO']
        seminar_ids = [r['content_id'] for r in page_slice if r['content_type'] == 'SEMINAR']

        article_map = {}
        if article_ids:
            for a in Article.objects.filter(
                id__in=article_ids,
                deletedAt__isnull=True,
            ).filter(Q(status='SYS26209B021')).only('id', 'title', 'subtitle', 'thumbnail', 'category'):
                article_map[a.id] = a

        video_map = {}
        seminar_map = {}
        vid_set = set(video_ids) | set(seminar_ids)
        if vid_set:
            for v in Video.objects.filter(
                id__in=list(vid_set),
                deletedAt__isnull=True,
                status=STATUS_PUBLISHED,
            ).only('id', 'title', 'subtitle', 'thumbnail', 'category', 'contentType'):
                if v.contentType == 'video':
                    video_map[v.id] = v
                elif v.contentType == 'seminar':
                    seminar_map[v.id] = v

        labels = {'ARTICLE': '아티클', 'VIDEO': '비디오', 'SEMINAR': '세미나'}
        qa_qs = (
            ContentQuestionAnswer.objects.filter(
                user_id=user_id,
                content_type__in=[row['content_type'] for row in page_slice],
                content_id__in=[row['content_id'] for row in page_slice],
            )
            .select_related('question')
            .order_by('content_type', 'content_id', 'question_id', 'answer_id')
        )
        qa_map = {}
        for qa in qa_qs:
            key = f"{qa.content_type}:{qa.content_id}"
            qa_map.setdefault(key, []).append(
                {
                    'questionId': qa.question_id,
                    'questionText': qa.question.question_text if qa.question_id and qa.question else '',
                    'answerId': qa.answer_id,
                    'answerText': qa.answer_text or '',
                    'createdAt': qa.created_at.isoformat() if qa.created_at else None,
                }
            )
        results = []
        for row in page_slice:
            ct = row['content_type']
            cid = row['content_id']
            if ct not in labels:
                continue
            meta = article_map.get(cid) if ct == 'ARTICLE' else video_map.get(cid) if ct == 'VIDEO' else seminar_map.get(cid)
            if meta is None:
                continue
            thumb_raw = getattr(meta, 'thumbnail', None) or None
            thumb_out = self._presign_article_thumb(thumb_raw) if ct == 'ARTICLE' else self._presign_video_thumb(thumb_raw)
            sub = (getattr(meta, 'subtitle', None) or '').strip() or None
            last_at = row['last_answered_at']
            results.append(
                {
                    'contentType': ct,
                    'contentTypeLabel': labels[ct],
                    'contentId': cid,
                    'categoryName': (getattr(meta, 'category', None) or '').strip() or None,
                    'title': meta.title,
                    'subtitle': sub,
                    'thumbnailUrl': thumb_out,
                    'lastAnsweredAt': last_at.isoformat() if last_at else None,
                    'answerCount': row['answer_count'],
                    'qaList': qa_map.get(f'{ct}:{cid}', []),
                }
            )

        return Response(
            create_success_response({'list': results, 'total': total, 'page': page, 'page_size': page_size}),
            status=status.HTTP_200_OK,
        )
