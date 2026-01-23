"""
CurrentSiteMiddleware
요청의 Host 헤더를 확인하여 사이트 정보를 request에 주입
"""
from django.utils.deprecation import MiddlewareMixin
from config.site_router import SITE_MAP


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


