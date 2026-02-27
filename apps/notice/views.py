from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination

from apps.board_auth import BoardJWTAuthentication, IsStaffOrReadOnly
from .models import Notice
from .serializers import (
    NoticeListSerializer,
    NoticeDetailSerializer,
    NoticeCreateUpdateSerializer,
)


class NoticePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class NoticeViewSet(viewsets.ModelViewSet):
    """
    공지사항 ViewSet.
    - 목록/상세: 전체 공개 (인증 없음, AllowAny)
    - 생성/수정/삭제: 관리자만 (BoardJWTAuthentication + IsStaffOrReadOnly)
    - 상세 조회 시 view_count 자동 증가
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # 기본 인증 없음 → list/retrieve 시 토큰 검사하지 않음
    queryset = Notice.objects.all()
    pagination_class = NoticePagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "content"]
    ordering_fields = ["created_at", "view_count", "title"]
    ordering = ["-is_pinned", "-created_at"]

    def get_serializer_class(self):
        action = getattr(self, "action", None)
        if action == "list":
            return NoticeListSerializer
        if action == "retrieve":
            return NoticeDetailSerializer
        return NoticeCreateUpdateSerializer

    def get_authenticators(self):
        # 인증 실행 시점에 self.action이 아직 설정되지 않으므로 request.method로 구분
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return []  # 조회: 인증 없음 (공지 목록/상세 공개)
        return [BoardJWTAuthentication()]

    def get_permissions(self):
        action = getattr(self, "action", None)
        if action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsStaffOrReadOnly()]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Notice.objects.filter(pk=instance.pk).update(
            view_count=instance.view_count + 1,
        )
        instance.refresh_from_db()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
