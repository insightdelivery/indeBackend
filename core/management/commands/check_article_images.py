"""
아티클 이미지 확인 명령어
특정 아티클의 이미지 파일이 S3에 존재하는지 확인
사용법: python manage.py check_article_images <article_id>
"""
from django.core.management.base import BaseCommand, CommandError
from core.s3_storage import get_s3_storage
from sites.admin_api.articles.utils import get_article_image_path


class Command(BaseCommand):
    help = '아티클의 이미지 파일이 S3에 존재하는지 확인'

    def add_arguments(self, parser):
        parser.add_argument('article_id', type=int, help='확인할 아티클 ID')

    def handle(self, *args, **options):
        article_id = options['article_id']
        
        self.stdout.write("=" * 60)
        self.stdout.write(f"아티클 {article_id}의 이미지 파일 확인")
        self.stdout.write("=" * 60)
        
        try:
            s3_storage = get_s3_storage()
            
            # 아티클 이미지 경로
            prefix = get_article_image_path(article_id)
            self.stdout.write(f"\n검색 경로: {prefix}")
            
            # 해당 경로의 모든 파일 목록 조회
            files = s3_storage.list_files(prefix=prefix)
            
            if not files:
                self.stdout.write(self.style.WARNING(f"\n⚠️  아티클 {article_id}의 이미지 파일을 찾을 수 없습니다."))
                return
            
            self.stdout.write(f"\n✅ 발견된 파일 ({len(files)}개):")
            self.stdout.write("-" * 60)
            
            for file_key in files:
                # 파일 정보 조회
                file_info = s3_storage.get_file_info(file_key)
                exists = s3_storage.file_exists(file_key)
                
                status = "✅ 존재" if exists else "❌ 없음"
                size = file_info.get('size', 0) if file_info else 0
                content_type = file_info.get('content_type', 'unknown') if file_info else 'unknown'
                
                self.stdout.write(f"{status} | {file_key}")
                self.stdout.write(f"      크기: {size} bytes, 타입: {content_type}")
                
                # Presigned URL 생성 테스트
                try:
                    presigned_url = s3_storage.get_file_url(file_key, expires_in=3600, force_presigned=True)
                    self.stdout.write(f"      Presigned URL: {presigned_url}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"      Presigned URL 생성 실패: {e}"))
                
                self.stdout.write("")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ 오류 발생: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())

