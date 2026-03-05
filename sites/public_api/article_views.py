"""
공개용 아티클 목록 API (frontend_www)
- 인증 불필요(AllowAny)
- status=published, 삭제되지 않은 글만 조회
- list-api.me 규칙 준수
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.core.paginator import Paginator

from sites.admin_api.articles.models import Article
from sites.admin_api.articles.serializers import ArticleListSerializer
from sites.admin_api.articles.utils import get_presigned_thumbnail_url
from core.utils import create_success_response, create_error_response


class PublicArticleListView(APIView):
    """
    공개 아티클 목록 조회
    GET /api/articles/
    - 인증 불필요
    - published, 미삭제만
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        """
        Query Parameters:
        - page: 페이지 번호 (기본 1)
        - pageSize: 페이지 크기 (기본 20)
        - category: 카테고리(sysCodeSid)
        - sort: latest(최신순) | popular(인기순)
        """
        try:
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('pageSize', 20)), 100)
            category = request.query_params.get('category', '').strip() or None
            sort = (request.query_params.get('sort') or 'latest').strip().lower()

            queryset = Article.objects.filter(
                deletedAt__isnull=True,
                status='published',
            )
            if category:
                queryset = queryset.filter(category=category)

            if sort == 'popular':
                queryset = queryset.order_by('-viewCount', '-createdAt')
            else:
                queryset = queryset.order_by('-createdAt')

            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            serializer = ArticleListSerializer(page_obj.object_list, many=True)
            articles_data = list(serializer.data)

            for article_data in articles_data:
                if article_data.get('thumbnail'):
                    article_data['thumbnail'] = get_presigned_thumbnail_url(
                        article_data['thumbnail'],
                        expires_in=3600,
                    )

            result = {
                'articles': articles_data,
                'total': paginator.count,
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
