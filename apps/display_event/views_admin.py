"""
관리자 DisplayEvent CRUD — AdminJWT
"""

from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from sites.admin_api.authentication import AdminJWTAuthentication

from .models import DisplayEvent
from .serializers import DisplayEventWriteSerializer
from .s3_utils import presign_event_banner_image_url


class AdminDisplayEventPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminDisplayEventViewSet(viewsets.ModelViewSet):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = DisplayEvent.objects.all()
    serializer_class = DisplayEventWriteSerializer
    pagination_class = AdminDisplayEventPagination

    def get_queryset(self):
        qs = DisplayEvent.objects.all().order_by("event_type_code", "display_order", "-id")
        et = self.request.query_params.get("eventTypeCode")
        ct = self.request.query_params.get("contentTypeCode")
        active = self.request.query_params.get("isActive")
        if et:
            qs = qs.filter(event_type_code=et.strip())
        if ct:
            qs = qs.filter(content_type_code=ct.strip())
        if active is not None and active != "":
            v = str(active).lower()
            if v in ("true", "1", "yes"):
                qs = qs.filter(is_active=True)
            elif v in ("false", "0", "no"):
                qs = qs.filter(is_active=False)
        return qs

    def _detail(self, instance):
        from .content_resolution import load_content
        from .hero_payload import build_hero_item

        content = load_content(instance.content_type_code, instance.content_id)
        data = build_hero_item(instance, content, include_admin_fields=True)
        iu = data.get("imageUrl")
        if iu:
            data["imageUrl"] = presign_event_banner_image_url(iu)
        return data

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response({"IndeAPIResponse": {"ErrorCode": "00", "Message": "ok", "Result": self._detail(instance)}})

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(
            {"IndeAPIResponse": {"ErrorCode": "00", "Message": "created", "Result": self._detail(obj)}},
            status=201,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        ser = self.get_serializer(instance, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response({"IndeAPIResponse": {"ErrorCode": "00", "Message": "ok", "Result": self._detail(obj)}})

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        iterable = page if page is not None else queryset
        rows = [self._detail(o) for o in iterable]
        if page is not None:
            return self.get_paginated_response(rows)
        return Response({"IndeAPIResponse": {"ErrorCode": "00", "Message": "ok", "Result": {"results": rows, "count": len(rows)}}})
