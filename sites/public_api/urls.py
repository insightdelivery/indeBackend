"""
공개 API URL 설정
"""
from django.urls import path
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from sites.public_api.views import RegisterView, LoginView


class PingView(APIView):
    """헬스체크용 Ping 엔드포인트"""
    
    def get(self, request):
        return Response({
            'status': 'ok',
            'site': 'public_api',
            'message': 'Public API is running'
        }, status=status.HTTP_200_OK)


urlpatterns = [
    path('ping/', PingView.as_view(), name='public_api_ping'),
    path('register/', RegisterView.as_view(), name='public_api_register'),
    path('register', RegisterView.as_view(), name='public_api_register_no_slash'),  # 슬래시 없음 지원
    path('api/register/', RegisterView.as_view(), name='public_api_register_api'),
    path('api/register', RegisterView.as_view(), name='public_api_register_api_no_slash'),
    path('login/', LoginView.as_view(), name='public_api_login'),
    path('login', LoginView.as_view(), name='public_api_login_no_slash'),
    path('api/login/', LoginView.as_view(), name='public_api_login_api'),
    path('api/login', LoginView.as_view(), name='public_api_login_api_no_slash'),
    # 여기에 추가 공개 API 엔드포인트 추가
]


