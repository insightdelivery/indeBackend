"""
공개용 아티클 목록/상세 API (frontend_www)
- 인증 불필요(AllowAny)
- status = 즉시발행(sysCode SYS26209B021)만, 삭제되지 않은 글만 조회
- list-api.me 규칙 준수
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db.models import F, Q
from django.utils import timezone

from sites.admin_api.articles.models import Article
from sites.admin_api.content_publish_syscodes import STATUS_PUBLISHED
from sites.public_api.models import ContentRankingCache
from sites.admin_api.articles.serializers import ArticleListSerializer, ArticleSerializer
from sites.admin_api.articles.utils import (
    get_presigned_thumbnail_url,
    convert_s3_urls_to_presigned,
)
from sites.admin_api.content_author.s3_utils import profile_image_to_presigned
from sites.public_api.article_preview import preview_content_html
from sites.public_api.library_useractivity_views import _get_member
from sites.public_api.content_share_service import resolve_share_token
from core.utils import create_success_response, create_error_response


def _public_client_ip(request):
    """공개 상세 조회수 중복 억제용 클라이언트 IP (비디오 상세와 동일 규칙)."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or '0'


def _article_share_entitlement(request, article_id: int) -> bool:
    """§10.5: share_access 쿠키의 share_token으로 DB 검증, ARTICLE·id 일치·미만료."""
    raw = request.COOKIES.get('share_access')
    if not raw:
        return False
    r = resolve_share_token(raw.strip())
    if not r or r.get('expired'):
        return False
    try:
        cid = int(r['content_id'])
    except (TypeError, ValueError):
        return False
    return r.get('content_type') == 'ARTICLE' and cid == int(article_id)


def _category_popular_content_order(category: str, base_date) -> list[str]:
    """
    CATEGORY_HOT 캐시 순서(최대 30) + 같은 카테고리 최신순 꼬리(비중복).
    schedulerContentPlan.md §C / categoryList.md §4.2
    """
    ranked = list(
        ContentRankingCache.objects.filter(
            ranking_type=ContentRankingCache.RANKING_CATEGORY_HOT,
            content_type='ARTICLE',
            category_code=category,
            base_date=base_date,
        )
        .order_by('rank_order')
        .values_list('content_code', flat=True)
    )
    seen: set[str] = set()
    ordered: list[str] = []
    for c in ranked:
        sc = str(c).strip()
        if not sc or sc in seen:
            continue
        seen.add(sc)
        ordered.append(sc)
    ranked_int: list[int] = []
    for c in ordered:
        try:
            ranked_int.append(int(c, 10))
        except ValueError:
            continue
    tail_qs = (
        Article.objects.filter(deletedAt__isnull=True, category=category)
        .filter(Q(status=STATUS_PUBLISHED))
        .order_by('-createdAt')
    )
    if ranked_int:
        tail_qs = tail_qs.exclude(id__in=ranked_int)
    tail_ids = tail_qs.values_list('id', flat=True)
    for pk in tail_ids:
        s = str(pk)
        if s not in seen:
            seen.add(s)
            ordered.append(s)
    return ordered


class PublicArticleListView(APIView):
    """
    공개 아티클 목록 조회
    GET /api/articles/
    - 인증 불필요
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        """
        Query Parameters:
        - page: 페이지 번호 (기본 1)
        - pageSize: 페이지 크기 (기본 20)
        - category: 카테고리(sysCodeSid)
        - author_id: 작성자(ContentAuthor) PK. 지정 시 해당 저자 글만 (editorList.md)
        - sort: latest(최신순) | popular(인기순)
          - popular + category: CATEGORY_HOT 캐시 + 동일 카테고리 최신순 꼬리(비중복)
          - popular + author_id(카테고리 없음 또는 author_id 동시 지정 시 HOT 미사용): viewCount 정렬
          - popular 단독: viewCount 정렬(카테고리 미지정 시)
        """
        try:
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('pageSize', 20)), 100)
            category = request.query_params.get('category', '').strip() or None
            sort = (request.query_params.get('sort') or 'latest').strip().lower()

            author_pk = None
            author_id_raw = request.query_params.get('author_id', '').strip()
            if author_id_raw:
                try:
                    author_pk = int(author_id_raw, 10)
                    if author_pk <= 0:
                        author_pk = None
                except ValueError:
                    author_pk = None

            queryset = Article.objects.filter(
                deletedAt__isnull=True,
            ).filter(
                Q(status=STATUS_PUBLISHED),
            ).select_related('author_id')
            if category:
                queryset = queryset.filter(category=category)
            if author_pk is not None:
                queryset = queryset.filter(author_id=author_pk)

            # CATEGORY_HOT는 카테고리 전용. author_id가 있으면 동일 캐시 경로 사용 안 함(editorList.md)
            if sort == 'popular' and category and author_pk is None:
                d = timezone.localdate()
                full_order = _category_popular_content_order(category, d)
                total = len(full_order)
                start = (page - 1) * page_size
                slice_codes = full_order[start : start + page_size]
                id_list: list[int] = []
                for c in slice_codes:
                    try:
                        id_list.append(int(str(c).strip(), 10))
                    except ValueError:
                        continue
                by_id = {
                    a.id: a
                    for a in Article.objects.filter(id__in=id_list).select_related('author_id')
                }
                page_objs: list = []
                for c in slice_codes:
                    try:
                        i = int(str(c).strip(), 10)
                    except ValueError:
                        continue
                    a = by_id.get(i)
                    if a:
                        page_objs.append(a)
                serializer = ArticleListSerializer(page_objs, many=True)
                articles_data = list(serializer.data)
            else:
                if sort == 'popular':
                    queryset = queryset.order_by('-viewCount', '-createdAt')
                else:
                    queryset = queryset.order_by('-createdAt')

                paginator = Paginator(queryset, page_size)
                page_obj = paginator.get_page(page)
                serializer = ArticleListSerializer(page_obj.object_list, many=True)
                articles_data = list(serializer.data)
                total = paginator.count

            for article_data in articles_data:
                if article_data.get('thumbnail'):
                    article_data['thumbnail'] = get_presigned_thumbnail_url(
                        article_data['thumbnail'],
                        expires_in=3600,
                    )
                if article_data.get('authorProfileImage'):
                    article_data['authorProfileImage'] = profile_image_to_presigned(
                        article_data['authorProfileImage'],
                        expires_in=3600,
                    )

            result = {
                'articles': articles_data,
                'total': total,
                'page': page,
                'pageSize': page_size,
            }
            return Response(
                create_success_response(result, '아티클 목록 조회 성공'),
                status=status.HTTP_200_OK,
            )
        except (ValueError, TypeError) as e:
            return Response(
                create_error_response(f'잘못된 요청 파라미터: {str(e)}'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                create_error_response(f'아티클 목록 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PublicArticleDetailView(APIView):
    """
    공개 아티클 상세 조회
    GET /api/articles/<id>/
    - 인증 선택: 유효 JWT(회원) → 본문 전체. 비회원 → content는 previewLength(0~100%)만큼만(태그 제거 후 글자 수 비율).
    - 응답 contentTruncated: 비회원이며 본문이 잘린 경우 true.
    - 발행된 글만 조회 (status SYS26209B021, 삭제 미포함)
    - 조회수: 동일 IP 기준 30초 내 1회만 article.viewCount 증가 (공개 비디오 상세와 동일)
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, id):
        try:
            article = Article.objects.filter(
                id=id,
                deletedAt__isnull=True,
            ).filter(
                Q(status=STATUS_PUBLISHED),
            ).select_related('author_id').first()

            if not article:
                return Response(
                    create_error_response('아티클을 찾을 수 없습니다.', '01'),
                    status=status.HTTP_404_NOT_FOUND,
                )

            ip = _public_client_ip(request)
            view_cache_key = f'public_article_detail_view:{id}:{ip}'
            if not cache.get(view_cache_key):
                Article.objects.filter(pk=article.pk).update(viewCount=F('viewCount') + 1)
                cache.set(view_cache_key, 1, 30)
            article.refresh_from_db(fields=['viewCount'])

            serializer = ArticleSerializer(article)
            data = serializer.data.copy()

            member = _get_member(request)
            is_member = member is not None
            share_ent = _article_share_entitlement(request, article.id)
            full_body = is_member or share_ent
            content_truncated = False
            if not full_body and data.get('content'):
                raw_content = data['content']
                pct = article.previewLength
                data['content'], content_truncated = preview_content_html(raw_content, pct)
            data['contentTruncated'] = content_truncated
            data['shareEntitlement'] = bool(share_ent and not is_member)

            if data.get('content'):
                data['content'] = convert_s3_urls_to_presigned(data['content'], expires_in=3600)
            if data.get('thumbnail'):
                data['thumbnail'] = get_presigned_thumbnail_url(data['thumbnail'], expires_in=3600)
            if data.get('authorProfileImage'):
                data['authorProfileImage'] = profile_image_to_presigned(
                    data['authorProfileImage'], expires_in=3600
                )

            resp = Response(
                create_success_response(data, '아티클 조회 성공'),
                status=status.HTTP_200_OK,
            )
            if share_ent and not is_member:
                resp['Cache-Control'] = 'private, no-store'
            return resp
        except Exception as e:
            return Response(
                create_error_response(f'아티클 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
