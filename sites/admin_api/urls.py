"""
관리자 API URL 설정
순환 import 방지를 위해 views를 지연 로드합니다.
"""
from django.conf import settings
from django.conf.urls.static import static
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
    
    # API v1 URL 패턴 (후행 슬래시 없음 — urlNoTrailingSlashPolicy)
    api_v1_patterns = [
        path('login', LoginView.as_view(), name='admin_api_login'),
        path('refresh', RefreshTokenView.as_view(), name='admin_api_refresh'),
        path('logout', LogoutView.as_view(), name='admin_api_logout'),
    ]

    return [
        path('ping', PingView.as_view(), name='admin_api_ping'),
        path('ping/', PingView.as_view(), name='admin_api_ping_slash'),

        # 기존 Account 기반 로그인 (하위 호환성)
        path('login', LoginView.as_view(), name='admin_api_login_legacy'),
        path('login/', LoginView.as_view(), name='admin_api_login_legacy_slash'),
        path('api/login', LoginView.as_view(), name='admin_api_login_api'),
        path('api/v1/', include(api_v1_patterns)),
        path('api/v1', include(api_v1_patterns)),
        path('refresh', RefreshTokenView.as_view(), name='admin_api_refresh_legacy'),
        path('api/refresh', RefreshTokenView.as_view(), name='admin_api_refresh_api'),
        path('logout', LogoutView.as_view(), name='admin_api_logout_legacy'),
        path('api/logout', LogoutView.as_view(), name='admin_api_logout_api'),

        # include 부모는 '.../xxx/' 형태여야 /xxx/<하위> 가 자식으로 전달됨 (Django path 규칙)
        path('adminMember/', include('api.adminMember.urls')),
        path('adminMember', include('api.adminMember.urls')),
        path('sysCodeManage/syscode/', include('sites.admin_api.sysCodeManage.urls')),
        path('sysCodeManage/syscode', include('sites.admin_api.sysCodeManage.urls')),
        path('systemmanage/', include('sites.admin_api.systemManage.urls')),
        path('systemmanage', include('sites.admin_api.systemManage.urls')),
        path('article/', include('sites.admin_api.articles.urls')),
        path('article', include('sites.admin_api.articles.urls')),
        path('authors/', include('sites.admin_api.content_author.urls')),
        path('authors', include('sites.admin_api.content_author.urls')),
        path('video/', include('sites.admin_api.video.urls')),
        path('video', include('sites.admin_api.video.urls')),
        path('files/', include('sites.admin_api.files.urls')),
        path('files', include('sites.admin_api.files.urls')),
        path('content/questions/', include('apps.content_question.admin_urls')),
        path('content/questions', include('apps.content_question.admin_urls')),
        path('board/', include('sites.admin_api.board.urls')),
        path('board', include('sites.admin_api.board.urls')),
        path('display-events/', include('apps.display_event.urls_admin')),
        path('display-events', include('apps.display_event.urls_admin')),
        path('publicMembers/', include('sites.admin_api.public_members.urls')),
        path('publicMembers', include('sites.admin_api.public_members.urls')),
        path('homepage-doc-info/', include('sites.admin_api.homepage_doc.urls')),
        path('homepage-doc-info', include('sites.admin_api.homepage_doc.urls')),
    ]

# urlpatterns를 함수에서 가져옴
urlpatterns = get_urlpatterns()
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

