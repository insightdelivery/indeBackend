from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views_admin import AdminDisplayEventViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r"", AdminDisplayEventViewSet, basename="admin-display-events")

urlpatterns = [
    path("", include(router.urls)),
]
