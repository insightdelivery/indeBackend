"""
AWS S3 연결 테스트 Django Management Command
사용법: python manage.py test_s3
"""
from django.core.management.base import BaseCommand
from core.s3_storage import get_s3_storage
from io import BytesIO
import os
import traceback


class Command(BaseCommand):
    help = 'AWS S3 연결 및 기본 기능 테스트'

    def handle(self, *args, **options):
        """S3 연결 및 기본 기능 테스트"""
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("AWS S3 연결 테스트 시작"))
        self.stdout.write("=" * 60)
        
        # 환경 변수 확인
        self.stdout.write("\n[1] 환경 변수 확인")
        self.stdout.write("-" * 60)
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', '')
        aws_region = os.getenv('AWS_S3_REGION_NAME', 'ap-northeast-2')
        bucket_dev = os.getenv('AWS_STORAGE_BUCKET_NAME_DEVELOPMENT', 'inde-develope')
        bucket_prod = os.getenv('AWS_STORAGE_BUCKET_NAME_PRODUCTION', 'inde-production')
        
        self.stdout.write(f"AWS_ACCESS_KEY_ID: {'✅ 설정됨' if aws_access_key else '❌ 미설정'}")
        self.stdout.write(f"AWS_SECRET_ACCESS_KEY: {'✅ 설정됨' if aws_secret_key else '❌ 미설정'}")
        self.stdout.write(f"AWS_S3_REGION_NAME: {aws_region}")
        self.stdout.write(f"AWS_STORAGE_BUCKET_NAME_DEVELOPMENT: {bucket_dev}")
        self.stdout.write(f"AWS_STORAGE_BUCKET_NAME_PRODUCTION: {bucket_prod}")
        
        if not aws_access_key or not aws_secret_key:
            self.stdout.write(self.style.ERROR("\n❌ AWS 인증 정보가 설정되지 않았습니다."))
            self.stdout.write("env/local/.env 파일에 AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY를 설정해주세요.")
            return
        
        # S3 Storage 인스턴스 생성
        self.stdout.write("\n[2] S3 Storage 인스턴스 생성")
        self.stdout.write("-" * 60)
        try:
            s3_storage = get_s3_storage()
            self.stdout.write(self.style.SUCCESS(f"✅ S3 Storage 인스턴스 생성 성공"))
            self.stdout.write(f"   사용 버킷: {s3_storage.bucket_name}")
            self.stdout.write(f"   리전: {s3_storage.aws_region}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ S3 Storage 인스턴스 생성 실패: {e}"))
            traceback.print_exc()
            return
        
        # 버킷 접근 테스트
        self.stdout.write("\n[3] 버킷 접근 테스트")
        self.stdout.write("-" * 60)
        try:
            # 버킷의 파일 목록 조회 (최대 1개만)로 접근 테스트
            files = s3_storage.list_files(prefix='', max_keys=1)
            self.stdout.write(self.style.SUCCESS(f"✅ 버킷 접근 성공"))
            self.stdout.write(f"   버킷 내 파일 수 (샘플): {len(files)}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 버킷 접근 실패: {e}"))
            traceback.print_exc()
            return
        
        # 파일 업로드 테스트
        self.stdout.write("\n[4] 파일 업로드 테스트")
        self.stdout.write("-" * 60)
        test_key = f"test/connection_test_{os.getpid()}.txt"
        test_content = "이것은 S3 연결 테스트 파일입니다.".encode('utf-8')
        
        try:
            file_obj = BytesIO(test_content)
            url = s3_storage.upload_file(
                file_obj=file_obj,
                key=test_key,
                content_type='text/plain',
                metadata={'test': 'true'}
            )
            self.stdout.write(self.style.SUCCESS(f"✅ 파일 업로드 성공"))
            self.stdout.write(f"   파일 키: {test_key}")
            self.stdout.write(f"   파일 URL: {url}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 파일 업로드 실패: {e}"))
            traceback.print_exc()
            return
        
        # 파일 존재 확인 테스트
        self.stdout.write("\n[5] 파일 존재 확인 테스트")
        self.stdout.write("-" * 60)
        try:
            exists = s3_storage.file_exists(test_key)
            if exists:
                self.stdout.write(self.style.SUCCESS(f"✅ 파일 존재 확인 성공"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ 파일이 존재하지 않습니다."))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 파일 존재 확인 실패: {e}"))
            traceback.print_exc()
            return
        
        # 파일 정보 조회 테스트
        self.stdout.write("\n[6] 파일 정보 조회 테스트")
        self.stdout.write("-" * 60)
        try:
            file_info = s3_storage.get_file_info(test_key)
            if file_info:
                self.stdout.write(self.style.SUCCESS(f"✅ 파일 정보 조회 성공"))
                self.stdout.write(f"   파일 크기: {file_info.get('size')} bytes")
                self.stdout.write(f"   Content-Type: {file_info.get('content_type')}")
                self.stdout.write(f"   수정일: {file_info.get('last_modified')}")
            else:
                self.stdout.write(self.style.ERROR(f"❌ 파일 정보를 가져올 수 없습니다."))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 파일 정보 조회 실패: {e}"))
            traceback.print_exc()
            return
        
        # 파일 URL 가져오기 테스트
        self.stdout.write("\n[7] 파일 URL 가져오기 테스트")
        self.stdout.write("-" * 60)
        try:
            file_url = s3_storage.get_file_url(test_key)
            self.stdout.write(self.style.SUCCESS(f"✅ 파일 URL 생성 성공"))
            self.stdout.write(f"   URL: {file_url}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 파일 URL 생성 실패: {e}"))
            traceback.print_exc()
            return
        
        # 파일 삭제 테스트
        self.stdout.write("\n[8] 파일 삭제 테스트")
        self.stdout.write("-" * 60)
        try:
            success = s3_storage.delete_file(test_key)
            if success:
                self.stdout.write(self.style.SUCCESS(f"✅ 파일 삭제 성공"))
                # 삭제 확인
                exists_after = s3_storage.file_exists(test_key)
                if not exists_after:
                    self.stdout.write(self.style.SUCCESS(f"✅ 삭제 확인 완료"))
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️  파일이 아직 존재합니다."))
            else:
                self.stdout.write(self.style.ERROR(f"❌ 파일 삭제 실패"))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 파일 삭제 실패: {e}"))
            traceback.print_exc()
            return
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ 모든 테스트 통과! S3 연결이 정상적으로 동작합니다."))
        self.stdout.write("=" * 60)

