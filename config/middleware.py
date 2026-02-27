"""
CurrentSiteMiddleware: 요청의 Host 헤더를 확인하여 사이트 정보를 request에 주입
SiteCorsMiddleware: site_meta['cors'] 기준으로 CORS 헤더 추가 (실서버 CORS 보장)
"""
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from config.site_router import SITE_MAP

# CORS 응답 헤더에 공통으로 쓸 값
CORS_ALLOW_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
CORS_ALLOW_HEADERS = "accept, accept-encoding, authorization, content-type, origin, x-csrftoken, x-requested-with"


def _add_cors_headers(response, origin):
    """응답에 CORS 헤더 추가"""
    if origin:
        response["Access-Control-Allow-Origin"] = origin
    response["Access-Control-Allow-Methods"] = CORS_ALLOW_METHODS
    response["Access-Control-Allow-Headers"] = CORS_ALLOW_HEADERS
    response["Access-Control-Allow-Credentials"] = "true"
    response["Access-Control-Max-Age"] = "86400"


class SiteCorsMiddleware(MiddlewareMixin):
    """
    site_meta['cors']에 등록된 Origin에 대해 CORS 헤더를 추가합니다.
    django-cors-headers 설정과 무관하게 api.inde.kr 등 도메인별 허용 목록을 적용해
    실서버 CORS 오류를 방지합니다.
    """

    def process_request(self, request):
        origin = request.META.get("HTTP_ORIGIN")
        site_meta = getattr(request, "site_meta", None)
        cors_list = site_meta.get("cors", []) if site_meta else []
        if request.method == "OPTIONS" and origin and origin in cors_list:
            response = HttpResponse(status=200)
            _add_cors_headers(response, origin)
            return response
        return None

    def process_response(self, request, response):
        origin = request.META.get("HTTP_ORIGIN")
        site_meta = getattr(request, "site_meta", None)
        cors_list = site_meta.get("cors", []) if site_meta else []
        if origin and origin in cors_list:
            _add_cors_headers(response, origin)
        return response


class CurrentSiteMiddleware(MiddlewareMixin):
    """
    Host 헤더를 기반으로 사이트 정보를 request에 주입하는 미들웨어
    request.site_meta에 다음 정보를 추가:
    - slug: 사이트 식별자 (admin_api, public_api 등)
    - urlconf: 해당 사이트의 URLConf 경로
    - cors: CORS 허용 도메인 리스트
    - media_prefix: 미디어 파일 prefix
    """
    
    def process_request(self, request):
        # Host 헤더에서 도메인 추출
        # nginx/로드밸런서 뒤에서 실행 시 X-Forwarded-Host 헤더도 확인
        host = request.get_host()
        
        # X-Forwarded-Host 헤더가 있으면 우선 사용 (프록시 환경)
        forwarded_host = request.META.get('HTTP_X_FORWARDED_HOST')
        if forwarded_host:
            # 여러 호스트가 쉼표로 구분되어 있을 수 있음 (첫 번째 것 사용)
            host = forwarded_host.split(',')[0].strip()
        
        # SITE_MAP에서 매칭되는 사이트 정보 찾기
        site_info = SITE_MAP.get(host)
        
        if site_info:
            # request에 사이트 메타 정보 주입
            request.site_meta = {
                'slug': site_info['slug'],
                'urlconf': site_info['urlconf'],
                'cors': site_info.get('cors', []),
                'media_prefix': site_info.get('media_prefix', ''),
            }
            
            # 동적 URLConf 설정
            request.urlconf = site_info['urlconf']
        else:
            # 매칭되는 사이트가 없으면 기본값 설정
            request.site_meta = {
                'slug': 'default',
                'urlconf': None,
                'cors': [],
                'media_prefix': '',
            }
        
        return None


