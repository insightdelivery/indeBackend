from django.urls import path

from .views_public import PublicDisplayEventListView

urlpatterns = [
    path("", PublicDisplayEventListView.as_view(), name="public_display_events_list"),
]
