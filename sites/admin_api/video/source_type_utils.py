"""영상 소스 유형(FILE_UPLOAD / VIMEO / YOUTUBE) 검증 — video·세미나(세미나는 FILE_UPLOAD만)."""

SOURCE_FILE_UPLOAD = 'FILE_UPLOAD'
SOURCE_VIMEO = 'VIMEO'
SOURCE_YOUTUBE = 'YOUTUBE'

SOURCE_CHOICES = [SOURCE_FILE_UPLOAD, SOURCE_VIMEO, SOURCE_YOUTUBE]


def is_youtube_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    u = url.strip().lower()
    return 'youtube.com/' in u or 'youtu.be/' in u


def is_vimeo_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    u = url.strip().lower()
    return 'vimeo.com' in u


def url_matches_source_type(source_type: str, url: str) -> bool:
    if not url or not str(url).strip():
        return False
    if source_type == SOURCE_YOUTUBE:
        return is_youtube_url(url)
    if source_type == SOURCE_VIMEO:
        return is_vimeo_url(url)
    return False


def infer_source_type_from_row(stream_id, video_url) -> str:
    """마이그레이션·레거시 행 백필용."""
    sid = (stream_id or '').strip()
    if sid:
        return SOURCE_FILE_UPLOAD
    url = (video_url or '').strip()
    if not url:
        return SOURCE_FILE_UPLOAD
    if is_youtube_url(url):
        return SOURCE_YOUTUBE
    if is_vimeo_url(url):
        return SOURCE_VIMEO
    return SOURCE_FILE_UPLOAD
