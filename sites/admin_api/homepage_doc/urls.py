from django.urls import path

from .views import AdminHomepageDocListView, AdminHomepageDocDetailView

urlpatterns = [
    path('', AdminHomepageDocListView.as_view(), name='admin_homepage_doc_list'),
    path('<str:doc_type>/', AdminHomepageDocDetailView.as_view(), name='admin_homepage_doc_detail'),
]
