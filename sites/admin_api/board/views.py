"""
관리자용 게시판 API (공지사항, FAQ, 1:1 문의)
동일 Notice/FAQ/Inquiry 모델 사용, AdminJWTAuthentication 적용.
"""
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter

from sites.admin_api.authentication import AdminJWTAuthentication
from apps.notice.models import Notice
from apps.notice.serializers import (
    NoticeListSerializer,
    NoticeDetailSerializer,
    NoticeCreateUpdateSerializer,
)
from apps.faq.models import FAQ
from apps.faq.serializers import FAQSerializer, FAQCreateUpdateSerializer
from apps.inquiry.models import Inquiry
from apps.inquiry.serializers import InquiryAnswerSerializer
from .serializers import AdminInquiryListSerializer, AdminInquiryDetailSerializer


class NoticePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminNoticeViewSet(viewsets.ModelViewSet):
    """관리자 공지사항 CRUD (AdminJWT)"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Notice.objects.all()
    pagination_class = NoticePagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "content"]
    ordering_fields = ["created_at", "view_count", "title"]
    ordering = ["-is_pinned", "-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return NoticeListSerializer
        if self.action == "retrieve":
            return NoticeDetailSerializer
        return NoticeCreateUpdateSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Notice.objects.filter(pk=instance.pk).update(
            view_count=instance.view_count + 1,
        )
        instance.refresh_from_db()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class FAQPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminFAQViewSet(viewsets.ModelViewSet):
    """관리자 FAQ CRUD (AdminJWT)"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = FAQ.objects.all()
    pagination_class = FAQPagination
    ordering = ["order"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return FAQSerializer
        return FAQCreateUpdateSerializer


class InquiryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50


class AdminInquiryViewSet(viewsets.ModelViewSet):
    """관리자 1:1 문의 목록/상세/답변 (AdminJWT), 목록/상세에 문의 회원 정보 포함"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Inquiry.objects.select_related("user").all()
    pagination_class = InquiryPagination
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return AdminInquiryListSerializer
        if self.action in ("partial_update", "update"):
            return InquiryAnswerSerializer
        return AdminInquiryDetailSerializer

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(status="answered")
        return Response(AdminInquiryDetailSerializer(instance).data)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
