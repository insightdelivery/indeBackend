from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InquiryViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r"", InquiryViewSet, basename="inquiry")

urlpatterns = [
    path("", include(router.urls)),
]
