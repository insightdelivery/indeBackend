"""
시스템 코드 관리 URL 설정
"""
from django.urls import path
from sites.admin_api.sysCodeManage.views import (
    SystemCodeTreeView,
    SystemCodeListView,
)

urlpatterns = [
    # 시스템 코드 트리 조회
    path('code_tree/', SystemCodeTreeView.as_view(), name='syscode_tree'),
    path('code_tree', SystemCodeTreeView.as_view(), name='syscode_tree_no_slash'),
    
    # 시스템 코드 목록 조회/생성
    path('', SystemCodeListView.as_view(), name='syscode_list'),
]



