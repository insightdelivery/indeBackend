"""
S3 설정 확인 명령어
프로덕션 환경에서 실제로 사용되는 S3 설정을 확인
사용법: python manage.py check_s3_config
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
from core.s3_storage import get_s3_storage


class Command(BaseCommand):
    help = 'S3 설정 및 버킷 정보 확인'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("S3 설정 확인")
        self.stdout.write("=" * 60)
        
        # 환경 변수 확인
        self.stdout.write("\n[1] 환경 변수 확인")
        self.stdout.write("-" * 60)
        django_debug = os.getenv('DJANGO_DEBUG', '0')
        settings_debug = getattr(settings, 'DEBUG', True)
        is_production = django_debug == '0' or not settings_debug
        
        self.stdout.write(f"DJANGO_DEBUG: {django_debug}")
        self.stdout.write(f"settings.DEBUG: {settings_debug}")
        self.stdout.write(f"is_production: {is_production}")
        
        self.stdout.write(f"\nAWS_ACCESS_KEY_ID: {'설정됨' if os.getenv('AWS_ACCESS_KEY_ID') else '❌ 미설정'}")
        self.stdout.write(f"AWS_SECRET_ACCESS_KEY: {'설정됨' if os.getenv('AWS_SECRET_ACCESS_KEY') else '❌ 미설정'}")
        self.stdout.write(f"AWS_S3_REGION_NAME: {os.getenv('AWS_S3_REGION_NAME', 'ap-northeast-2')}")
        
        # 버킷 설정 확인
        self.stdout.write("\n[2] 버킷 설정 확인")
        self.stdout.write("-" * 60)
        explicit_bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None) or os.getenv('AWS_STORAGE_BUCKET_NAME')
        bucket_dev = getattr(settings, 'AWS_STORAGE_BUCKET_NAME_DEVELOPMENT', None) or os.getenv('AWS_STORAGE_BUCKET_NAME_DEVELOPMENT', 'inde-develope')
        bucket_prod = getattr(settings, 'AWS_STORAGE_BUCKET_NAME_PRODUCTION', None) or os.getenv('AWS_STORAGE_BUCKET_NAME_PRODUCTION', 'inde-production')
        
        self.stdout.write(f"AWS_STORAGE_BUCKET_NAME (명시적): {explicit_bucket or '미설정'}")
        self.stdout.write(f"AWS_STORAGE_BUCKET_NAME_DEVELOPMENT: {bucket_dev}")
        self.stdout.write(f"AWS_STORAGE_BUCKET_NAME_PRODUCTION: {bucket_prod}")
        
        # 실제 사용되는 버킷 확인
        try:
            s3_storage = get_s3_storage()
            actual_bucket = s3_storage.bucket_name
            self.stdout.write(f"\n✅ 실제 사용되는 버킷: {actual_bucket}")
            self.stdout.write(f"✅ 리전: {s3_storage.aws_region}")
            
            # 버킷 접근 테스트
            self.stdout.write("\n[3] 버킷 접근 테스트")
            self.stdout.write("-" * 60)
            try:
                # 버킷 존재 여부 확인
                s3_storage.s3_client.head_bucket(Bucket=actual_bucket)
                self.stdout.write(f"✅ 버킷 '{actual_bucket}' 접근 가능")
                
                # 버킷 권한 확인 (간단한 목록 조회)
                response = s3_storage.s3_client.list_objects_v2(
                    Bucket=actual_bucket,
                    MaxKeys=1
                )
                self.stdout.write(f"✅ 버킷 '{actual_bucket}' 읽기 권한 확인됨")
                
            except Exception as e:
                error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', 'Unknown') if hasattr(e, 'response') else 'Unknown'
                self.stdout.write(self.style.ERROR(f"❌ 버킷 '{actual_bucket}' 접근 실패: {error_code} - {str(e)}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ S3 Storage 초기화 실패: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())

