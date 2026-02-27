from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminNoticeViewSet, AdminFAQViewSet, AdminInquiryViewSet

router = DefaultRouter()
router.register(r"notices", AdminNoticeViewSet, basename="admin-notices")
router.register(r"faqs", AdminFAQViewSet, basename="admin-faqs")
router.register(r"inquiries", AdminInquiryViewSet, basename="admin-inquiries")

urlpatterns = [
    path("", include(router.urls)),
]
