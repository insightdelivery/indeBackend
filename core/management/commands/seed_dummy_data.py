"""
더미 데이터 삽입 (아티클 · 비디오 · 세미나)
규칙: _docsRules/backend/DummyData.me

- 다시 실행하면 기존 더미 데이터는 삭제 후 지정한 개수만큼 새로 생성합니다.
- 썸네일: §6.2 C에 따라 더미 이미지를 S3에 업로드 후 반환 URL을 thumbnail에 저장합니다.

사용법:
  python manage.py seed_dummy_data --article 50
"""
import base64
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.request import urlopen

from django.core.management.base import BaseCommand
from django.db import connection

from sites.admin_api.articles.models import Article
from sites.admin_api.articles.utils import upload_thumbnail_to_s3

# sysCode 테이블 없을 때 사용할 기본 카테고리
DEFAULT_CATEGORY_IDS = ['category_article_01']

# §6.3 썸네일: 기독교 관련, 크기 1200x630(16:9 계열). §6.2 C: S3 업로드용 이미지
THUMBNAIL_WIDTH = 1200
THUMBNAIL_HEIGHT = 630

# 더미 썸네일 이미지: 이 경로에 thumbnail.jpg 또는 thumbnail.png 있으면 사용, 없으면 URL에서 1회 다운로드
COMMAND_DIR = Path(__file__).resolve().parent
DUMMY_MEDIA_DIR = COMMAND_DIR / "dummy_media"
PLACEHOLDER_IMAGE_URL = f"https://placehold.co/{THUMBNAIL_WIDTH}x{THUMBNAIL_HEIGHT}/jpeg?text=Article"

# 캐시: 한 번만 읽거나 다운로드
_dummy_thumbnail_base64_cache = None


def get_dummy_thumbnail_base64() -> Optional[str]:
    """
    §6.2 C: 더미 썸네일 이미지를 base64 데이터 URL로 반환.
    dummy_media/thumbnail.jpg 또는 .png가 있으면 사용, 없으면 placehold.co에서 1회 다운로드.
    """
    global _dummy_thumbnail_base64_cache
    if _dummy_thumbnail_base64_cache is not None:
        return _dummy_thumbnail_base64_cache

    # 1) 로컬 파일 우선
    for name in ("thumbnail.jpg", "thumbnail.png", "thumbnail.jpeg"):
        path = DUMMY_MEDIA_DIR / name
        if path.exists():
            try:
                raw = path.read_bytes()
                ext = path.suffix.lstrip(".")
                b64 = base64.b64encode(raw).decode("ascii")
                _dummy_thumbnail_base64_cache = f"data:image/{ext};base64,{b64}"
                return _dummy_thumbnail_base64_cache
            except Exception:
                break

    # 2) URL에서 1회 다운로드
    try:
        with urlopen(PLACEHOLDER_IMAGE_URL, timeout=10) as resp:
            raw = resp.read()
        b64 = base64.b64encode(raw).decode("ascii")
        _dummy_thumbnail_base64_cache = "data:image/jpeg;base64," + b64
        return _dummy_thumbnail_base64_cache
    except Exception:
        pass

    return None


# 2026년 1월 1일 00:00 ~ 3월 31일 23:59
def random_datetime_2026_jan_mar():
    start = datetime(2026, 1, 1, 0, 0, 0)
    end = datetime(2026, 3, 31, 23, 59, 59)
    delta_sec = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, delta_sec))


def get_article_content_about_500_chars(n: int) -> str:
    """§3.1: content 필수, 500자 정도 되는 HTML 또는 평문."""
    return (
        f"<p>더미 본문입니다. (ID: {n})</p>"
        "<p>개발/테스트용 데이터입니다. 이 글은 더미 아티클의 본문 내용이며, "
        "기독교 관련 콘텐츠와 인사이트를 나누는 공간에서 사용되는 예시 텍스트입니다. "
        "실제 서비스에서는 다양한 주제의 글이 게시됩니다. 본문은 500자 정도로 작성하는 것이 "
        "권장되며, 리스트와 상세 화면에서 미리보기 및 전체 본문 표시에 활용됩니다. "
        "여기에 추가 문장을 넣어 500자 분량에 맞춥니다. 마지막으로 한 줄 더 적어 "
        "본문 길이가 500자 내외가 되도록 합니다.</p>"
    )


def get_category_syscode_ids():
    """
    sysCode 테이블에서 sysCodeParentsSid='SYS26209B002' 인 sysCodeSid 목록 반환.
    테이블이 없거나 조회 실패 시 DEFAULT_CATEGORY_IDS 사용.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT sysCodeSid FROM sysCodeManager WHERE sysCodeParentsSid = %s LIMIT 100",
                ['SYS26209B002'],
            )
            rows = cursor.fetchall()
        ids = [r[0] for r in rows if r and r[0] and len(str(r[0])) <= 50]
        return ids if ids else DEFAULT_CATEGORY_IDS
    except Exception:
        return DEFAULT_CATEGORY_IDS


class Command(BaseCommand):
    help = '아티클/비디오/세미나 더미 데이터 삽입 (DummyData.me 규칙)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--article',
            type=int,
            default=0,
            metavar='N',
            help='삽입할 아티클 더미 개수 (0이면 아티클 미실행). 실행 시 기존 더미는 삭제 후 새로 생성.',
        )

    def handle(self, *args, **options):
        article_count = options.get('article', 0)
        if article_count > 0:
            self._seed_articles(article_count)

    def _seed_articles(self, count: int):
        # 기존 더미 아티클 삭제 후 새로 생성
        deleted, _ = Article.objects.filter(title__startswith='더미 아티클 제목').delete()
        if deleted:
            self.stdout.write(self.style.WARNING(f'기존 더미 아티클 {deleted}건 삭제됨.'))

        category_ids = get_category_syscode_ids()
        authors = [f'더미 작성자 {i}' for i in range(1, 11)]  # 10명 번갈아 사용
        statuses = ['published'] * 8 + ['draft'] * 2  # 80% published, 20% draft

        # §6.2 C: S3 업로드용 더미 이미지 base64 (1회만 로드/다운로드)
        thumbnail_base64 = get_dummy_thumbnail_base64()
        if not thumbnail_base64:
            self.stdout.write(
                self.style.WARNING(
                    "더미 썸네일 이미지를 찾을 수 없습니다. "
                    f"'{DUMMY_MEDIA_DIR}'에 thumbnail.jpg를 넣거나 네트워크를 확인하세요. thumbnail=null로 생성합니다."
                )
            )

        created_ids = []
        for n in range(1, count + 1):
            category = random.choice(category_ids)
            author = random.choice(authors)
            status = random.choice(statuses)
            is_editor_pick = n <= 5  # 처음 5건만 에디터 픽

            article = Article.objects.create(
                title=f'더미 아티클 제목 {n}',
                subtitle=f'더미 부제목 {n}' if n % 3 != 0 else '',
                content=get_article_content_about_500_chars(n),
                thumbnail=None,
                category=category,
                author=author,
                authorAffiliation='인디 매거진',
                visibility='all',
                status=status,
                isEditorPick=is_editor_pick,
                viewCount=random.randint(0, 500),
                commentCount=random.randint(0, 20),
                tags=['태그1', '태그2'] if n % 2 == 0 else [],
                questions=['Q1?', 'Q2?'] if n % 4 == 0 else [],
            )
            created_ids.append(article.id)

            # §6.2 C: 썸네일을 S3에 업로드 후 URL 저장
            if thumbnail_base64:
                s3_url = upload_thumbnail_to_s3(thumbnail_base64, article.id)
                if s3_url:
                    article.thumbnail = s3_url
                    article.save(update_fields=['thumbnail'])

        # createdAt, updatedAt 을 2026년 1~3월 랜덤으로 설정 (update()로 auto_now 우회)
        for pk in created_ids:
            dt = random_datetime_2026_jan_mar()
            Article.objects.filter(pk=pk).update(createdAt=dt, updatedAt=dt)

        self.stdout.write(self.style.SUCCESS(f'아티클 더미 {count}건 삽입 완료 (ID: {min(created_ids)} ~ {max(created_ids)})'))
