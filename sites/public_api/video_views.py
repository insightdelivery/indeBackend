"""
공개용 비디오 목록 API (frontend_www 메인 등)
- 인증 불필요(AllowAny)
- contentType=video, 삭제 제외, status=public 만
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.core.paginator import Paginator

from sites.admin_api.video.models import Video
from sites.admin_api.video.serializers import VideoListSerializer
from sites.admin_api.video.utils import get_presigned_thumbnail_url
from core.utils import create_success_response, create_error_response


class PublicVideoListView(APIView):
    """
    공개 비디오 목록 조회
    GET /api/videos/
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            page = int(request.query_params.get("page", 1))
            page_size = min(int(request.query_params.get("pageSize", 20)), 100)
            sort = (request.query_params.get("sort") or "latest").strip().lower()

            queryset = Video.objects.filter(
                deletedAt__isnull=True,
                contentType="video",
                status="public",
            )
            if sort == "popular":
                queryset = queryset.order_by("-viewCount", "-createdAt")
            else:
                queryset = queryset.order_by("-createdAt")

            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            serializer = VideoListSerializer(page_obj.object_list, many=True)
            items = list(serializer.data)

            for row in items:
                if row.get("thumbnail"):
                    row["thumbnail"] = get_presigned_thumbnail_url(
                        row["thumbnail"],
                        expires_in=3600,
                    )

            result = {
                "videos": items,
                "total": paginator.count,
                "page": page,
                "pageSize": page_size,
            }
            return Response(
                create_success_response(result, "비디오 목록 조회 성공"),
                status=status.HTTP_200_OK,
            )
        except (ValueError, TypeError) as e:
            return Response(
                create_error_response(f"잘못된 요청 파라미터: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                create_error_response(f"비디오 목록 조회 실패: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
