"""
공개용 비디오 목록/상세 API (frontend_www)
- 인증 불필요(AllowAny)
- 목록: contentType=video, 삭제 제외, status=public 만
- 상세: video/seminar 공개 행 단건 (frontend_www 상세·세미나 상세 공용)
"""
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.core.paginator import Paginator
from django.db.models import F
from django.core.cache import cache

from sites.admin_api.video.models import Video
from sites.admin_api.video.serializers import VideoListSerializer, VideoSerializer
from sites.admin_api.video.utils import get_presigned_thumbnail_url
from core.utils import create_success_response, create_error_response
from core.cloudflare_stream import get_cloudflare_stream

logger = logging.getLogger(__name__)


def _public_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or "0"


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
            category = (request.query_params.get("category") or "").strip() or None
            content_type = (request.query_params.get("contentType") or "video").strip().lower()
            if content_type not in ("video", "seminar"):
                content_type = "video"

            queryset = Video.objects.filter(
                deletedAt__isnull=True,
                contentType=content_type,
                status="public",
            )
            if category:
                queryset = queryset.filter(category=category)
            if sort == "popular":
                queryset = queryset.order_by("-viewCount", "-createdAt")
            elif sort == "rating":
                queryset = queryset.order_by(
                    F("rating").desc(nulls_last=True), "-createdAt"
                )
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


class PublicVideoDetailView(APIView):
    """
    공개 비디오/세미나 상세
    GET /api/videos/<id>/
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, id):
        try:
            video = (
                Video.objects.filter(
                    id=id,
                    deletedAt__isnull=True,
                    status="public",
                )
                .first()
            )

            if not video:
                return Response(
                    create_error_response("비디오를 찾을 수 없습니다.", "01"),
                    status=status.HTTP_404_NOT_FOUND,
                )

            ip = _public_client_ip(request)
            view_cache_key = f"public_video_detail_view:{id}:{ip}"
            if not cache.get(view_cache_key):
                Video.objects.filter(pk=video.pk).update(viewCount=F("viewCount") + 1)
                cache.set(view_cache_key, 1, 30)
            video.refresh_from_db(fields=["viewCount"])

            serializer = VideoSerializer(video)
            data = serializer.data.copy()

            if video.videoStreamId:
                try:
                    cf_stream = get_cloudflare_stream()
                    video_info = cf_stream.get_video(video.videoStreamId)
                    data["videoStreamInfo"] = {
                        "embedUrl": cf_stream.get_video_embed_url(video.videoStreamId),
                        "thumbnailUrl": cf_stream.get_video_thumbnail_url(
                            video.videoStreamId
                        ),
                        "hlsUrl": cf_stream.get_video_hls_url(video.videoStreamId),
                        "dashUrl": cf_stream.get_video_dash_url(video.videoStreamId),
                        "status": video_info.get("status"),
                        "duration": video_info.get("duration"),
                        "size": video_info.get("size"),
                        "width": video_info.get("width"),
                        "height": video_info.get("height"),
                    }
                except Exception as e:
                    logger.warning(
                        "공개 비디오 상세: Cloudflare Stream 정보 조회 실패: %s", e
                    )
                    data["videoStreamInfo"] = None
            else:
                data["videoStreamInfo"] = None

            if data.get("thumbnail"):
                data["thumbnail"] = get_presigned_thumbnail_url(
                    data["thumbnail"],
                    expires_in=3600,
                )

            return Response(
                create_success_response(data, "비디오 조회 성공"),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error("공개 비디오 상세 조회 실패: %s", e, exc_info=True)
            return Response(
                create_error_response(f"비디오 조회 실패: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
