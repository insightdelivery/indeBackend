from django.urls import path

from .views import CurationDetailView, CurationListCreateView, CurationPreviewView

urlpatterns = [
    path('preview', CurationPreviewView.as_view(), name='admin_curation_preview'),
    path('preview/', CurationPreviewView.as_view(), name='admin_curation_preview_slash'),
    path('<int:pk>', CurationDetailView.as_view(), name='admin_curation_detail'),
    path('<int:pk>/', CurationDetailView.as_view(), name='admin_curation_detail_slash'),
    path('', CurationListCreateView.as_view(), name='admin_curation_list'),
]
