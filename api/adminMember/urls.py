"""
관리자 회원 API URL 설정
순환 import 방지를 위해 views를 지연 로드합니다.
"""
from django.urls import path

# 순환 import 방지를 위해 views를 함수 내부에서 import
def get_urlpatterns():
    from api.adminMember.views import (
        AdminRegisterView, 
        AdminLoginView, 
        AdminLogoutView, 
        TokenRefreshView,
        AdminListView,
        AdminUpdateView,
        AdminDeleteView
    )
    
    return [
        # 회원 가입: /adminMember/join
        path('join/', AdminRegisterView.as_view(), name='admin_member_join'),
        path('join', AdminRegisterView.as_view(), name='admin_member_join_no_slash'),
        
        # 로그인: /adminMember/login
        path('login/', AdminLoginView.as_view(), name='admin_member_login'),
        path('login', AdminLoginView.as_view(), name='admin_member_login_no_slash'),
        
        # 토큰 갱신: /adminMember/tokenrefresh
        path('tokenrefresh/', TokenRefreshView.as_view(), name='admin_member_token_refresh'),
        path('tokenrefresh', TokenRefreshView.as_view(), name='admin_member_token_refresh_no_slash'),
        
        # 로그아웃: /adminMember/logout
        path('logout/', AdminLogoutView.as_view(), name='admin_member_logout'),
        path('logout', AdminLogoutView.as_view(), name='admin_member_logout_no_slash'),
        
        # 관리자 목록: /adminMember/list
        path('list/', AdminListView.as_view(), name='admin_member_list'),
        path('list', AdminListView.as_view(), name='admin_member_list_no_slash'),
        
        # 관리자 수정: /adminMember/update
        path('update/', AdminUpdateView.as_view(), name='admin_member_update'),
        path('update', AdminUpdateView.as_view(), name='admin_member_update_no_slash'),
        
        # 관리자 삭제: /adminMember/delete
        path('delete/', AdminDeleteView.as_view(), name='admin_member_delete'),
        path('delete', AdminDeleteView.as_view(), name='admin_member_delete_no_slash'),
    ]

# urlpatterns를 함수에서 가져옴
urlpatterns = get_urlpatterns()

