"""
관리자 API URL 설정
"""
from django.urls import path, include
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from sites.admin_api.views import LoginView, RefreshTokenView, LogoutView
from api.adminMember.urls import urlpatterns as admin_member_urls


class PingView(APIView):
    """헬스체크용 Ping 엔드포인트"""
    
    def get(self, request):
        return Response({
            'status': 'ok',
            'site': 'admin_api',
            'message': 'Admin API is running'
        }, status=status.HTTP_200_OK)


# API v1 URL 패턴
api_v1_patterns = [
    path('login/', LoginView.as_view(), name='admin_api_login'),
    path('refresh/', RefreshTokenView.as_view(), name='admin_api_refresh'),
    path('logout/', LogoutView.as_view(), name='admin_api_logout'),
]

urlpatterns = [
    path('ping/', PingView.as_view(), name='admin_api_ping'),
    
    # 기존 Account 기반 로그인 (하위 호환성)
    path('login/', LoginView.as_view(), name='admin_api_login_legacy'),
    path('api/login/', LoginView.as_view(), name='admin_api_login_api'),
    path('api/login', LoginView.as_view(), name='admin_api_login_api_no_slash'),
    path('api/v1/', include(api_v1_patterns)),
    path('refresh/', RefreshTokenView.as_view(), name='admin_api_refresh_legacy'),
    path('api/refresh/', RefreshTokenView.as_view(), name='admin_api_refresh_api'),
    path('api/refresh', RefreshTokenView.as_view(), name='admin_api_refresh_api_no_slash'),
    path('logout/', LogoutView.as_view(), name='admin_api_logout_legacy'),
    path('api/logout/', LogoutView.as_view(), name='admin_api_logout_api'),
    path('api/logout', LogoutView.as_view(), name='admin_api_logout_api_no_slash'),
    
    # 관리자 회원 API (AdminMemberShip 기반)
    path('adminMember/', include(admin_member_urls)),
    
    # 여기에 추가 관리자 API 엔드포인트 추가
]

