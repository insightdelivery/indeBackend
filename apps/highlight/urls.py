"""
Article Highlight API URL (articleHightlightPlan.md §5)
"""
from django.urls import path
from .views import HighlightListCreateView, HighlightDeleteView, HighlightGroupDeleteView

urlpatterns = [
    path('', HighlightListCreateView.as_view(), name='highlight_list_create'),
    path('group/<int:highlight_group_id>/', HighlightGroupDeleteView.as_view(), name='highlight_group_delete'),
    path('<int:highlight_id>/', HighlightDeleteView.as_view(), name='highlight_delete'),
]
