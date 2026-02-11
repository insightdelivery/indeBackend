"""
AWS S3 연결 테스트 스크립트
"""
import os
import sys
import django
from pathlib import Path

# Django 설정 로드
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from core.s3_storage import get_s3_storage
from io import BytesIO
import traceback


def test_s3_connection():
    """S3 연결 및 기본 기능 테스트"""
    print("=" * 60)
    print("AWS S3 연결 테스트 시작")
    print("=" * 60)
    
    # 환경 변수 확인
    print("\n[1] 환경 변수 확인")
    print("-" * 60)
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    aws_region = os.getenv('AWS_S3_REGION_NAME', 'ap-northeast-2')
    bucket_dev = os.getenv('AWS_STORAGE_BUCKET_NAME_DEVELOPMENT', 'inde-develope')
    bucket_prod = os.getenv('AWS_STORAGE_BUCKET_NAME_PRODUCTION', 'inde-production')
    
    print(f"AWS_ACCESS_KEY_ID: {'설정됨' if aws_access_key else '❌ 미설정'}")
    print(f"AWS_SECRET_ACCESS_KEY: {'설정됨' if aws_secret_key else '❌ 미설정'}")
    print(f"AWS_S3_REGION_NAME: {aws_region}")
    print(f"AWS_STORAGE_BUCKET_NAME_DEVELOPMENT: {bucket_dev}")
    print(f"AWS_STORAGE_BUCKET_NAME_PRODUCTION: {bucket_prod}")
    
    if not aws_access_key or not aws_secret_key:
        print("\n❌ AWS 인증 정보가 설정되지 않았습니다.")
        print("env/local/.env 파일에 AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY를 설정해주세요.")
        return False
    
    # S3 Storage 인스턴스 생성
    print("\n[2] S3 Storage 인스턴스 생성")
    print("-" * 60)
    try:
        s3_storage = get_s3_storage()
        print(f"✅ S3 Storage 인스턴스 생성 성공")
        print(f"   사용 버킷: {s3_storage.bucket_name}")
        print(f"   리전: {s3_storage.aws_region}")
    except Exception as e:
        print(f"❌ S3 Storage 인스턴스 생성 실패: {e}")
        traceback.print_exc()
        return False
    
    # 버킷 접근 테스트
    print("\n[3] 버킷 접근 테스트")
    print("-" * 60)
    try:
        # 버킷의 파일 목록 조회 (최대 1개만)로 접근 테스트
        files = s3_storage.list_files(prefix='', max_keys=1)
        print(f"✅ 버킷 접근 성공")
        print(f"   버킷 내 파일 수 (샘플): {len(files)}")
    except Exception as e:
        print(f"❌ 버킷 접근 실패: {e}")
        traceback.print_exc()
        return False
    
    # 파일 업로드 테스트
    print("\n[4] 파일 업로드 테스트")
    print("-" * 60)
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
        print(f"✅ 파일 업로드 성공")
        print(f"   파일 키: {test_key}")
        print(f"   파일 URL: {url}")
    except Exception as e:
        print(f"❌ 파일 업로드 실패: {e}")
        traceback.print_exc()
        return False
    
    # 파일 존재 확인 테스트
    print("\n[5] 파일 존재 확인 테스트")
    print("-" * 60)
    try:
        exists = s3_storage.file_exists(test_key)
        if exists:
            print(f"✅ 파일 존재 확인 성공")
        else:
            print(f"❌ 파일이 존재하지 않습니다.")
            return False
    except Exception as e:
        print(f"❌ 파일 존재 확인 실패: {e}")
        traceback.print_exc()
        return False
    
    # 파일 정보 조회 테스트
    print("\n[6] 파일 정보 조회 테스트")
    print("-" * 60)
    try:
        file_info = s3_storage.get_file_info(test_key)
        if file_info:
            print(f"✅ 파일 정보 조회 성공")
            print(f"   파일 크기: {file_info.get('size')} bytes")
            print(f"   Content-Type: {file_info.get('content_type')}")
            print(f"   수정일: {file_info.get('last_modified')}")
        else:
            print(f"❌ 파일 정보를 가져올 수 없습니다.")
            return False
    except Exception as e:
        print(f"❌ 파일 정보 조회 실패: {e}")
        traceback.print_exc()
        return False
    
    # 파일 URL 가져오기 테스트
    print("\n[7] 파일 URL 가져오기 테스트")
    print("-" * 60)
    try:
        file_url = s3_storage.get_file_url(test_key)
        print(f"✅ 파일 URL 생성 성공")
        print(f"   URL: {file_url}")
    except Exception as e:
        print(f"❌ 파일 URL 생성 실패: {e}")
        traceback.print_exc()
        return False
    
    # 파일 삭제 테스트
    print("\n[8] 파일 삭제 테스트")
    print("-" * 60)
    try:
        success = s3_storage.delete_file(test_key)
        if success:
            print(f"✅ 파일 삭제 성공")
            # 삭제 확인
            exists_after = s3_storage.file_exists(test_key)
            if not exists_after:
                print(f"✅ 삭제 확인 완료")
            else:
                print(f"⚠️  파일이 아직 존재합니다.")
        else:
            print(f"❌ 파일 삭제 실패")
            return False
    except Exception as e:
        print(f"❌ 파일 삭제 실패: {e}")
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 통과! S3 연결이 정상적으로 동작합니다.")
    print("=" * 60)
    return True


if __name__ == '__main__':
    success = test_s3_connection()
    sys.exit(0 if success else 1)

