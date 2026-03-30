from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InquiryViewSet
from .email_open_view import inquiry_email_open

router = DefaultRouter(trailing_slash=False)
router.register(r"", InquiryViewSet, basename="inquiry")

urlpatterns = [
    # 메일 열람 추적(1x1 GIF) — router PK 경로보다 먼저 매칭
    path("email-open/<str:token>", inquiry_email_open, name="inquiry-email-open"),
    path("", include(router.urls)),
]
