"""
도메인 기반 라우팅 설정
각 도메인(Host 헤더)에 따라 URLConf를 동적으로 선택
"""
SITE_MAP = {
    # 프로덕션 도메인
    "admin_api.inde.kr": {
        "slug": "admin_api",
        "urlconf": "sites.admin_api.urls",
        "cors": ["https://admin.inde.kr"],
        "media_prefix": "admin",
    },
    "api.inde.kr": {
        "slug": "public_api",
        "urlconf": "sites.public_api.urls",
        "cors": ["https://www.inde.kr"],
        "media_prefix": "public",
    },
    
    # 로컬 개발 환경: 포트별로 사이트 분리
    "localhost:8000": {
        "slug": "admin_api",
        "urlconf": "sites.admin_api.urls",
        "cors": ["http://localhost:3000"],
        "media_prefix": "local",
    },
    "localhost:8001": {
        "slug": "public_api",
        "urlconf": "sites.public_api.urls",
        "cors": ["http://localhost:3000"],
        "media_prefix": "local",
    },
    "127.0.0.1:8000": {
        "slug": "admin_api",
        "urlconf": "sites.admin_api.urls",
        "cors": ["http://localhost:3000"],
        "media_prefix": "local",
    },
    "127.0.0.1:8001": {
        "slug": "public_api",
        "urlconf": "sites.public_api.urls",
        "cors": ["http://localhost:3000"],
        "media_prefix": "local",
    },
}


