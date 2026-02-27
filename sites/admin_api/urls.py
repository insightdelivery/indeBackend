"""
관리자 API URL 설정
순환 import 방지를 위해 views를 지연 로드합니다.
"""
from django.urls import path, include
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status


class PingView(APIView):
    """헬스체크용 Ping 엔드포인트"""
    
    def get(self, request):
        return Response({
            'status': 'ok',
            'site': 'admin_api',
            'message': 'Admin API is running'
        }, status=status.HTTP_200_OK)


# 순환 import 방지를 위해 views를 지연 로드
def get_urlpatterns():
    from sites.admin_api.views import LoginView, RefreshTokenView, LogoutView
    
    # API v1 URL 패턴
    api_v1_patterns = [
        path('login/', LoginView.as_view(), name='admin_api_login'),
        path('refresh/', RefreshTokenView.as_view(), name='admin_api_refresh'),
        path('logout/', LogoutView.as_view(), name='admin_api_logout'),
    ]
    
    return [
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
        # 순환 import 방지를 위해 문자열로 전달
        path('adminMember/', include('api.adminMember.urls')),
        
        # 시스템 코드 관리 API
        path('sysCodeManage/syscode/', include('sites.admin_api.sysCodeManage.urls')),
        
        # SystemManage CRUD API (참고 프로젝트 구조)
        path('systemmanage/', include('sites.admin_api.systemManage.urls')),
        
        # 아티클 관리 API
        path('article/', include('sites.admin_api.articles.urls')),
        
        # 비디오/세미나 관리 API
        path('video/', include('sites.admin_api.video.urls')),
        
        # 파일 관리 API (S3)
        path('files/', include('sites.admin_api.files.urls')),
        
        # 게시판 관리 API (공지/FAQ/1:1문의)
        path('board/', include('sites.admin_api.board.urls')),
        # 공개 회원(PublicMemberShip) 관리 API
        path('publicMembers/', include('sites.admin_api.public_members.urls')),
    ]

# urlpatterns를 함수에서 가져옴
urlpatterns = get_urlpatterns()

