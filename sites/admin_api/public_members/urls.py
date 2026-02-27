from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminPublicMemberViewSet

router = DefaultRouter()
router.register(r"", AdminPublicMemberViewSet, basename="admin-public-members")

urlpatterns = [
    path("", include(router.urls)),
]
