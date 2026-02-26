from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination

from apps.board_auth import BoardJWTAuthentication
from .models import Inquiry
from .serializers import (
    InquiryListSerializer,
    InquiryDetailSerializer,
    InquiryCreateSerializer,
    InquiryAnswerSerializer,
)


class InquiryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50


class InquiryViewSet(viewsets.ModelViewSet):
    """
    1:1 문의 ViewSet.
    - 작성: 로그인 회원만 (IsAuthenticated)
    - 목록/상세: 본인 문의만 조회 (관리자는 전체)
    - 답변 수정: 관리자만 (IsAdminUser), answer 저장 시 status='answered' 자동 변경
    """
    authentication_classes = [BoardJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = InquiryDetailSerializer
    pagination_class = InquiryPagination

    def get_queryset(self):
        user = self.request.user
        if not getattr(user, "member", None):
            return Inquiry.objects.none()
        if getattr(user, "is_staff", False):
            return Inquiry.objects.all()
        return Inquiry.objects.filter(user_id=user.member.member_sid)

    def get_serializer_class(self):
        action = getattr(self, "action", None)
        if action == "list":
            return InquiryListSerializer
        if action == "create":
            return InquiryCreateSerializer
        if action in ("partial_update", "update"):
            request = getattr(self, "request", None)
            if request and getattr(request.user, "is_staff", False):
                return InquiryAnswerSerializer
            return InquiryDetailSerializer
        return InquiryDetailSerializer

    def get_permissions(self):
        action = getattr(self, "action", None)
        if action in ("partial_update", "update", "destroy"):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user.member)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(status="answered")
        return Response(InquiryDetailSerializer(instance).data)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
