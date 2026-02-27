"""
관리자용 PublicMemberShip CRUD API (AdminJWT)
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter

from sites.admin_api.authentication import AdminJWTAuthentication
from sites.public_api.models import PublicMemberShip
from .serializers import (
    PublicMemberListSerializer,
    PublicMemberDetailSerializer,
    PublicMemberCreateUpdateSerializer,
)


class PublicMemberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminPublicMemberViewSet(viewsets.ModelViewSet):
    """관리자 공개 회원(PublicMemberShip) CRUD"""
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = PublicMemberShip.objects.all()
    pagination_class = PublicMemberPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["email", "name", "nickname", "phone"]
    ordering_fields = ["member_sid", "email", "created_at", "last_login"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return PublicMemberListSerializer
        if self.action == "retrieve":
            return PublicMemberDetailSerializer
        return PublicMemberCreateUpdateSerializer
