from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.pagination import PageNumberPagination

from apps.board_auth import BoardJWTAuthentication
from .models import FAQ
from .serializers import FAQSerializer, FAQCreateUpdateSerializer


class FAQPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class FAQViewSet(viewsets.ModelViewSet):
    """
    FAQ ViewSet.
    - 목록/상세: 전체 공개 (인증 없음, AllowAny)
    - 생성/수정/삭제: 관리자만 (BoardJWTAuthentication + IsAdminUser)
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    queryset = FAQ.objects.all()
    pagination_class = FAQPagination
    ordering = ["order"]

    def get_serializer_class(self):
        action = getattr(self, "action", None)
        if action in ("list", "retrieve"):
            return FAQSerializer
        return FAQCreateUpdateSerializer

    def get_authenticators(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return []
        return [BoardJWTAuthentication()]

    def get_permissions(self):
        action = getattr(self, "action", None)
        if action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAdminUser()]
