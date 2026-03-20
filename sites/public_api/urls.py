"""
공개 API URL 설정
"""
from django.urls import path, include
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from sites.public_api.views import RegisterView, LoginView, VerifyEmailView, ResendVerificationEmailView, MeView, ProfileCompleteView, TokenRefreshView
from sites.public_api.syscode_views import SysCodeByParentView, SysCodeBulkByParentsView
from sites.public_api.google_oauth import GoogleRedirectView, GoogleCallbackView
from sites.public_api.naver_oauth import NaverRedirectView, NaverCallbackView
from sites.public_api.library_useractivity_views import (
    LibraryUserActivityView,
    LibraryUserActivityRating,
    LibraryUserActivityBookmark,
    LibraryStatsViewCount,
    LibraryStatsRating,
    LibraryStatsBookmark,
    LibraryMeViews,
    LibraryMeBookmarks,
    LibraryMeRatings,
)


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
    path('register', RegisterView.as_view(), name='public_api_register_no_slash'),
    path('api/register/', RegisterView.as_view(), name='public_api_register_api'),
    path('api/register', RegisterView.as_view(), name='public_api_register_api_no_slash'),
    path('auth/register/', RegisterView.as_view(), name='public_api_auth_register'),
    path('auth/register', RegisterView.as_view(), name='public_api_auth_register_no_slash'),
    path('login/', LoginView.as_view(), name='public_api_login'),
    path('login', LoginView.as_view(), name='public_api_login_no_slash'),
    path('api/login/', LoginView.as_view(), name='public_api_login_api'),
    path('api/login', LoginView.as_view(), name='public_api_login_api_no_slash'),
    path('auth/login/', LoginView.as_view(), name='public_api_auth_login'),
    path('auth/login', LoginView.as_view(), name='public_api_auth_login_no_slash'),
    path('auth/tokenrefresh/', TokenRefreshView.as_view(), name='public_api_auth_token_refresh'),
    path('auth/tokenrefresh', TokenRefreshView.as_view(), name='public_api_auth_token_refresh_no_slash'),
    path('auth/verify-email/', VerifyEmailView.as_view(), name='public_api_verify_email'),
    path('auth/verify-email', VerifyEmailView.as_view(), name='public_api_verify_email_no_slash'),
    path('auth/resend-verification-email/', ResendVerificationEmailView.as_view(), name='public_api_resend_verification'),
    path('auth/resend-verification-email', ResendVerificationEmailView.as_view(), name='public_api_resend_verification_no_slash'),
    path('auth/google/redirect/', GoogleRedirectView.as_view(), name='public_api_google_redirect'),
    path('auth/google/redirect', GoogleRedirectView.as_view(), name='public_api_google_redirect_no_slash'),
    path('auth/google/callback/', GoogleCallbackView.as_view(), name='public_api_google_callback'),
    path('auth/google/callback', GoogleCallbackView.as_view(), name='public_api_google_callback_no_slash'),
    path('auth/naver/redirect/', NaverRedirectView.as_view(), name='public_api_naver_redirect'),
    path('auth/naver/redirect', NaverRedirectView.as_view(), name='public_api_naver_redirect_no_slash'),
    path('auth/naver/callback/', NaverCallbackView.as_view(), name='public_api_naver_callback'),
    path('auth/naver/callback', NaverCallbackView.as_view(), name='public_api_naver_callback_no_slash'),
    path('me/', MeView.as_view(), name='public_api_me'),
    path('me', MeView.as_view(), name='public_api_me_no_slash'),
    path('profile/complete/', ProfileCompleteView.as_view(), name='public_api_profile_complete'),
    path('profile/complete', ProfileCompleteView.as_view(), name='public_api_profile_complete_no_slash'),
    # 시스템 코드 읽기 전용 (홈페이지 회원가입/프로필 등용, 관리자 API와 동일 경로로 호환)
    path('systemmanage/syscode/by_parent/', SysCodeByParentView.as_view(), name='public_api_syscode_by_parent'),
    path('systemmanage/syscode/by_parent', SysCodeByParentView.as_view(), name='public_api_syscode_by_parent_no_slash'),
    path('systemmanage/syscode/bulk/', SysCodeBulkByParentsView.as_view(), name='public_api_syscode_bulk'),
    path('systemmanage/syscode/bulk', SysCodeBulkByParentsView.as_view(), name='public_api_syscode_bulk_no_slash'),
    # 공지/FAQ/1:1 문의 게시판
    path('api/notices/', include('apps.notice.urls')),
    path('api/faqs/', include('apps.faq.urls')),
    path('api/inquiries/', include('apps.inquiry.urls')),
    # 공개 아티클 목록 (frontend_www)
    path('api/articles/', include('sites.public_api.article_urls')),
    path('api/videos/', include('sites.public_api.video_urls')),
    path('api/events/', include('apps.display_event.urls_public')),
    # 아티클 하이라이트 (articleHightlightPlan.md)
    path('api/highlights/', include('apps.highlight.urls')),
    # 콘텐츠 질문/답변 (공개)
    path('api/content/', include('apps.content_question.public_urls')),
    # 라이브러리 사용자 활동 (userPublicActiviteLog.md)
    path('api/library/useractivity/view/', LibraryUserActivityView.as_view()),
    path('api/library/useractivity/rating/', LibraryUserActivityRating.as_view()),
    path('api/library/useractivity/bookmark/', LibraryUserActivityBookmark.as_view()),
    path('api/library/useractivity/me/views/', LibraryMeViews.as_view()),
    path('api/library/useractivity/me/bookmarks/', LibraryMeBookmarks.as_view()),
    path('api/library/useractivity/me/ratings/', LibraryMeRatings.as_view()),
    path('api/library/stats/view-count/', LibraryStatsViewCount.as_view()),
    path('api/library/stats/rating/', LibraryStatsRating.as_view()),
    path('api/library/stats/bookmark/', LibraryStatsBookmark.as_view()),
]


