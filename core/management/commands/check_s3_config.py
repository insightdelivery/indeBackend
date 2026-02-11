"""
S3 설정 확인 명령어
프로덕션 환경에서 실제로 사용되는 S3 설정을 확인
사용법: python manage.py check_s3_config
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import os
from core.s3_storage import get_s3_storage


class Command(BaseCommand):
    help = 'S3 설정 및 버킷 정보 확인'

    def handle(self, *args, **options):
        # env/.env 파일의 ENV_MODE에 따라 적절한 .env 파일 로드
        base_dir = Path(settings.BASE_DIR) if hasattr(settings, 'BASE_DIR') else Path(__file__).resolve().parents[3]
        
        from dotenv import load_dotenv
        
        # 1. 먼저 메인 .env 파일 로드하여 ENV_MODE 확인
        main_env_path = base_dir / 'env' / '.env'
        if main_env_path.exists():
            load_dotenv(main_env_path)
            self.stdout.write(f"✅ 메인 환경 변수 파일 로드: {main_env_path}")
        else:
            self.stdout.write(self.style.WARNING(f"⚠️  메인 환경 변수 파일을 찾을 수 없습니다: {main_env_path}"))
        
        # 2. ENV_MODE 확인
        env_mode = os.getenv('ENV_MODE', 'local').lower()
        self.stdout.write(f"ENV_MODE: {env_mode}")
        
        # 3. ENV_MODE에 따라 적절한 환경 변수 파일 로드
        if env_mode == 'production':
            env_file_path = base_dir / 'env' / '.env.production'
            env_name = 'production'
        else:  # local 또는 기본값
            env_file_path = base_dir / 'env' / '.env.local'
            env_name = 'local'
        
        if env_file_path.exists():
            load_dotenv(env_file_path, override=True)  # override=True로 메인 .env의 값을 덮어씀
            self.stdout.write(f"✅ {env_name} 환경 변수 파일 로드: {env_file_path}")
        else:
            self.stdout.write(self.style.WARNING(f"⚠️  {env_name} 환경 변수 파일을 찾을 수 없습니다: {env_file_path}"))
        
        # 설정 모듈 확인
        settings_module = os.getenv('DJANGO_SETTINGS_MODULE', 'config.settings.local')
        self.stdout.write(f"현재 설정 모듈: {settings_module}")
        
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
        
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        self.stdout.write(f"\nAWS_ACCESS_KEY_ID: {'✅ 설정됨' if aws_access_key else '❌ 미설정'}")
        self.stdout.write(f"AWS_SECRET_ACCESS_KEY: {'✅ 설정됨' if aws_secret_key else '❌ 미설정'}")
        self.stdout.write(f"AWS_S3_REGION_NAME: {os.getenv('AWS_S3_REGION_NAME', 'ap-northeast-2')}")
        
        # 환경 변수 파일 경로 확인
        self.stdout.write(f"\n환경 변수 파일 경로:")
        self.stdout.write(f"  .env.production: {env_prod_path}")
        self.stdout.write(f"  파일 존재: {'✅ 있음' if env_prod_path.exists() else '❌ 없음'}")
        
        if not aws_access_key or not aws_secret_key:
            self.stdout.write(self.style.ERROR("\n❌ AWS 인증 정보가 설정되지 않았습니다."))
            self.stdout.write(f"환경 변수 파일을 확인하세요: {env_file_path}")
            if env_file_path.exists():
                self.stdout.write("파일 내용 확인:")
                try:
                    with open(env_file_path, 'r') as f:
                        lines = f.readlines()
                        aws_lines = [line for line in lines if 'AWS' in line and not line.strip().startswith('#')]
                        if aws_lines:
                            for line in aws_lines:
                                # 값은 마스킹
                                if '=' in line:
                                    key, value = line.split('=', 1)
                                    masked_value = value[:3] + '***' if len(value.strip()) > 3 else '***'
                                    self.stdout.write(f"  {key.strip()}={masked_value.strip()}")
                                else:
                                    self.stdout.write(f"  {line.strip()}")
                        else:
                            self.stdout.write("  AWS 관련 환경 변수가 파일에 없습니다.")
                except Exception as e:
                    self.stdout.write(f"  파일 읽기 실패: {e}")
            return
        
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

