"""
공개 API URL 설정
"""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from sites.public_api.views import (
    RegisterView,
    LoginView,
    OAuthPendingClaimsView,
    SignupEmailAvailabilityView,
    OAuthCompleteSignupView,
    VerifyEmailView,
    ResendVerificationEmailView,
    MeView,
    MeEmailAvailabilityView,
    VerifyProfilePasswordView,
    ProfileCompleteView,
    TokenRefreshView,
    PublicLogoutView,
)
from sites.public_api.sms_views import (
    SendSmsVerificationView,
    VerifySmsVerificationView,
    SendProfilePhoneSmsView,
)
from sites.public_api.account_recovery_views import (
    SendSmsFindIdView,
    FindIdView,
    SendPasswordResetCodeView,
    VerifyPasswordResetCodeView,
    ResetPasswordView,
)
from sites.public_api.syscode_views import (
    SysCodeByParentView,
    SysCodeBulkByParentsView,
    SysCodeListByParentsSidView,
)
from sites.public_api.google_oauth import GoogleRedirectView, GoogleCallbackView
from sites.public_api.naver_oauth import NaverRedirectView, NaverCallbackView
from sites.public_api.kakao_oauth import KakaoRedirectView, KakaoCallbackView
from sites.public_api.homepage_doc_views import PublicHomepageDocDetailView
from sites.public_api.site_visit_views import SiteVisitRecordView
from sites.public_api.library_useractivity_views import (
    LibraryUserActivityView,
    LibraryUserActivityShare,
    LibraryUserActivityRating,
    LibraryUserActivityBookmark,
    LibraryStatsViewCount,
    LibraryStatsRating,
    LibraryStatsBookmark,
    LibraryMeViews,
    LibraryMeBookmarks,
    LibraryMeRatings,
)
from sites.public_api.content_share_views import (
    LibraryContentShareEnsure,
    LibraryContentShareResolve,
    LibraryContentShareVisit,
    LibraryContentShareForCopy,
)
from sites.public_api.content_ranking_views import (
    LibraryRankingHotView,
    LibraryRankingRecommendedView,
    LibraryRankingShareView,
    LibraryRankingWeeklyCrossView,
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
    path('auth/logout/', PublicLogoutView.as_view(), name='public_api_auth_logout'),
    path('auth/logout', PublicLogoutView.as_view(), name='public_api_auth_logout_no_slash'),
    path('auth/verify-email/', VerifyEmailView.as_view(), name='public_api_verify_email'),
    path('auth/verify-email', VerifyEmailView.as_view(), name='public_api_verify_email_no_slash'),
    path('auth/resend-verification-email/', ResendVerificationEmailView.as_view(), name='public_api_resend_verification'),
    path('auth/resend-verification-email', ResendVerificationEmailView.as_view(), name='public_api_resend_verification_no_slash'),
    path('auth/oauth-pending-claims/', OAuthPendingClaimsView.as_view(), name='public_api_oauth_pending_claims'),
    path('auth/oauth-pending-claims', OAuthPendingClaimsView.as_view(), name='public_api_oauth_pending_claims_no_slash'),
    path('auth/signup-email-availability/', SignupEmailAvailabilityView.as_view(), name='public_api_signup_email_availability'),
    path('auth/signup-email-availability', SignupEmailAvailabilityView.as_view(), name='public_api_signup_email_availability_no_slash'),
    path('auth/oauth-complete-signup/', OAuthCompleteSignupView.as_view(), name='public_api_oauth_complete_signup'),
    path('auth/oauth-complete-signup', OAuthCompleteSignupView.as_view(), name='public_api_oauth_complete_signup_no_slash'),
    path('auth/send-sms/', SendSmsVerificationView.as_view(), name='public_api_send_sms'),
    path('auth/send-sms', SendSmsVerificationView.as_view(), name='public_api_send_sms_no_slash'),
    path('auth/verify-sms/', VerifySmsVerificationView.as_view(), name='public_api_verify_sms'),
    path('auth/verify-sms', VerifySmsVerificationView.as_view(), name='public_api_verify_sms_no_slash'),
    path('auth/send-sms-profile-phone/', SendProfilePhoneSmsView.as_view(), name='public_api_send_sms_profile_phone'),
    path('auth/send-sms-profile-phone', SendProfilePhoneSmsView.as_view(), name='public_api_send_sms_profile_phone_no_slash'),
    path('auth/send-sms-find-id/', SendSmsFindIdView.as_view(), name='public_api_send_sms_find_id'),
    path('auth/send-sms-find-id', SendSmsFindIdView.as_view(), name='public_api_send_sms_find_id_no_slash'),
    path('auth/find-id/', FindIdView.as_view(), name='public_api_find_id'),
    path('auth/find-id', FindIdView.as_view(), name='public_api_find_id_no_slash'),
    path('auth/send-password-reset-code/', SendPasswordResetCodeView.as_view(), name='public_api_send_pw_reset'),
    path('auth/send-password-reset-code', SendPasswordResetCodeView.as_view(), name='public_api_send_pw_reset_no_slash'),
    path('auth/verify-password-reset-code/', VerifyPasswordResetCodeView.as_view(), name='public_api_verify_pw_reset'),
    path('auth/verify-password-reset-code', VerifyPasswordResetCodeView.as_view(), name='public_api_verify_pw_reset_no_slash'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='public_api_reset_password'),
    path('auth/reset-password', ResetPasswordView.as_view(), name='public_api_reset_password_no_slash'),
    path('auth/verify-profile-password/', VerifyProfilePasswordView.as_view(), name='public_api_verify_profile_password'),
    path('auth/verify-profile-password', VerifyProfilePasswordView.as_view(), name='public_api_verify_profile_password_no_slash'),
    path('auth/google/redirect/', GoogleRedirectView.as_view(), name='public_api_google_redirect'),
    path('auth/google/redirect', GoogleRedirectView.as_view(), name='public_api_google_redirect_no_slash'),
    path('auth/google/callback/', GoogleCallbackView.as_view(), name='public_api_google_callback'),
    path('auth/google/callback', GoogleCallbackView.as_view(), name='public_api_google_callback_no_slash'),
    path('auth/naver/redirect/', NaverRedirectView.as_view(), name='public_api_naver_redirect'),
    path('auth/naver/redirect', NaverRedirectView.as_view(), name='public_api_naver_redirect_no_slash'),
    path('auth/naver/callback/', NaverCallbackView.as_view(), name='public_api_naver_callback'),
    path('auth/naver/callback', NaverCallbackView.as_view(), name='public_api_naver_callback_no_slash'),
    path('auth/kakao/redirect/', KakaoRedirectView.as_view(), name='public_api_kakao_redirect'),
    path('auth/kakao/redirect', KakaoRedirectView.as_view(), name='public_api_kakao_redirect_no_slash'),
    path('auth/kakao/callback/', KakaoCallbackView.as_view(), name='public_api_kakao_callback'),
    path('auth/kakao/callback', KakaoCallbackView.as_view(), name='public_api_kakao_callback_no_slash'),
    path('me/', MeView.as_view(), name='public_api_me'),
    path('me', MeView.as_view(), name='public_api_me_no_slash'),
    path('me/email-availability/', MeEmailAvailabilityView.as_view(), name='public_api_me_email_availability'),
    path('me/email-availability', MeEmailAvailabilityView.as_view(), name='public_api_me_email_availability_no_slash'),
    path('profile/complete/', ProfileCompleteView.as_view(), name='public_api_profile_complete'),
    path('profile/complete', ProfileCompleteView.as_view(), name='public_api_profile_complete_no_slash'),
    # 시스템 코드 읽기 전용 (홈페이지 회원가입/프로필 등용, 관리자 API와 동일 경로로 호환)
    path('systemmanage/syscode/by_parent/', SysCodeByParentView.as_view(), name='public_api_syscode_by_parent'),
    path('systemmanage/syscode/by_parent', SysCodeByParentView.as_view(), name='public_api_syscode_by_parent_no_slash'),
    path('systemmanage/syscode/bulk/', SysCodeBulkByParentsView.as_view(), name='public_api_syscode_bulk'),
    path('systemmanage/syscode/bulk', SysCodeBulkByParentsView.as_view(), name='public_api_syscode_bulk_no_slash'),
    # GET /systemmanage/syscode?sysCodeParentsSid= — by_parent와 동일 쿼리(관리자 list 호환)
    path('systemmanage/syscode/', SysCodeListByParentsSidView.as_view(), name='public_api_syscode_list'),
    path('systemmanage/syscode', SysCodeListByParentsSidView.as_view(), name='public_api_syscode_list_no_slash'),
    # 공지/FAQ/1:1 문의 게시판 (후행 슬래시 없이 매칭 — urlNoTrailingSlashPolicy)
    # include() 부모에 '.../xxx/' 가 있어야 /api/xxx/<하위> 가 자식 urlconf로 넘어감 (Django path 규칙)
    path('api/notices/', include('apps.notice.urls')),
    path('api/notices', include('apps.notice.urls')),
    path('api/faqs/', include('apps.faq.urls')),
    path('api/faqs', include('apps.faq.urls')),
    path('api/inquiries/', include('apps.inquiry.urls')),
    path('api/inquiries', include('apps.inquiry.urls')),
    # 공개 아티클 목록 (frontend_www)
    path('api/homepage-docs/<str:doc_type>', PublicHomepageDocDetailView.as_view(), name='public_homepage_doc_detail'),
    path('api/homepage-docs/<str:doc_type>/', PublicHomepageDocDetailView.as_view(), name='public_homepage_doc_detail_slash'),
    path('api/articles/', include('sites.public_api.article_urls')),
    path('api/articles', include('sites.public_api.article_urls')),
    path('api/videos/', include('sites.public_api.video_urls')),
    path('api/videos', include('sites.public_api.video_urls')),
    path('api/search/', include('sites.public_api.search_urls')),
    path('api/search', include('sites.public_api.search_urls')),
    path('api/events/', include('apps.display_event.urls_public')),
    path('api/events', include('apps.display_event.urls_public')),
    # 아티클 하이라이트 (articleHightlightPlan.md)
    path('api/highlights/', include('apps.highlight.urls')),
    path('api/highlights', include('apps.highlight.urls')),
    # 콘텐츠 질문/답변 (공개)
    path('api/content/', include('apps.content_question.public_urls')),
    path('api/content', include('apps.content_question.public_urls')),
    # 콘텐츠 댓글 (공개)
    path('api/', include('apps.content_comments.public_urls')),
    path('api', include('apps.content_comments.public_urls')),
    # 라이브러리 사용자 활동 (userPublicActiviteLog.md)
    path('api/site-visits', SiteVisitRecordView.as_view()),
    path('api/site-visits/', SiteVisitRecordView.as_view()),
    path('api/library/useractivity/view', LibraryUserActivityView.as_view()),
    path('api/library/useractivity/view/', LibraryUserActivityView.as_view()),
    path('api/library/useractivity/share', LibraryUserActivityShare.as_view()),
    path('api/library/useractivity/share/', LibraryUserActivityShare.as_view()),
    path('api/library/content-share/ensure', LibraryContentShareEnsure.as_view()),
    path('api/library/content-share/ensure/', LibraryContentShareEnsure.as_view()),
    path('api/library/content-share/resolve', LibraryContentShareResolve.as_view()),
    path('api/library/content-share/resolve/', LibraryContentShareResolve.as_view()),
    path('api/library/content-share/visit', LibraryContentShareVisit.as_view()),
    path('api/library/content-share/visit/', LibraryContentShareVisit.as_view()),
    path('api/library/content-share/for-copy', LibraryContentShareForCopy.as_view()),
    path('api/library/content-share/for-copy/', LibraryContentShareForCopy.as_view()),
    path('api/library/useractivity/rating', LibraryUserActivityRating.as_view()),
    path('api/library/useractivity/rating/', LibraryUserActivityRating.as_view()),
    path('api/library/useractivity/bookmark', LibraryUserActivityBookmark.as_view()),
    path('api/library/useractivity/bookmark/', LibraryUserActivityBookmark.as_view()),
    path('api/library/useractivity/me/views', LibraryMeViews.as_view()),
    path('api/library/useractivity/me/views/', LibraryMeViews.as_view()),
    path('api/library/useractivity/me/bookmarks', LibraryMeBookmarks.as_view()),
    path('api/library/useractivity/me/bookmarks/', LibraryMeBookmarks.as_view()),
    path('api/library/useractivity/me/ratings', LibraryMeRatings.as_view()),
    path('api/library/useractivity/me/ratings/', LibraryMeRatings.as_view()),
    path('api/library/stats/view-count', LibraryStatsViewCount.as_view()),
    path('api/library/stats/view-count/', LibraryStatsViewCount.as_view()),
    path('api/library/stats/rating', LibraryStatsRating.as_view()),
    path('api/library/stats/rating/', LibraryStatsRating.as_view()),
    path('api/library/stats/bookmark', LibraryStatsBookmark.as_view()),
    path('api/library/stats/bookmark/', LibraryStatsBookmark.as_view()),
    path('api/library/ranking/hot', LibraryRankingHotView.as_view()),
    path('api/library/ranking/hot/', LibraryRankingHotView.as_view()),
    path('api/library/ranking/share', LibraryRankingShareView.as_view()),
    path('api/library/ranking/share/', LibraryRankingShareView.as_view()),
    path('api/library/ranking/recommended', LibraryRankingRecommendedView.as_view()),
    path('api/library/ranking/recommended/', LibraryRankingRecommendedView.as_view()),
    path('api/library/ranking/weekly', LibraryRankingWeeklyCrossView.as_view()),
    path('api/library/ranking/weekly/', LibraryRankingWeeklyCrossView.as_view()),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


