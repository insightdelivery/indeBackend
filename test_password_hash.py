#!/usr/bin/env python
"""
비밀번호 해시화 테스트 프로그램
데이터베이스에 저장될 때 비밀번호가 어떻게 처리되는지 확인합니다.
"""
import os
import sys
import django

# Django 설정 로드
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth.hashers import make_password, check_password, get_hasher
from api.models import AdminMemberShip
import json

def print_separator(title=""):
    """구분선 출력"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print('='*60)
    else:
        print('-'*60)

def test_password_hashing():
    """비밀번호 해시화 테스트"""
    print_separator("비밀번호 해시화 테스트 프로그램")
    
    # 테스트할 비밀번호들
    test_passwords = [
        "njh7351!",
        "Test@1234",
        "한글비밀번호123",
        "a" * 100,  # 긴 비밀번호
    ]
    
    for i, raw_password in enumerate(test_passwords, 1):
        print_separator(f"테스트 {i}: 비밀번호 = '{raw_password}'")
        
        # 1. 원본 비밀번호 출력
        print(f"\n[1] 원본 비밀번호:")
        print(f"    길이: {len(raw_password)} 문자")
        print(f"    내용: {raw_password}")
        
        # 2. 해시화
        hashed_password = make_password(raw_password)
        print(f"\n[2] 해시화된 비밀번호:")
        print(f"    길이: {len(hashed_password)} 문자")
        print(f"    내용: {hashed_password}")
        
        # 3. 해시 알고리즘 정보 추출
        try:
            hasher = get_hasher()
            print(f"\n[3] 사용된 해시 알고리즘:")
            print(f"    알고리즘: {hasher.algorithm}")
            print(f"    알고리즘 이름: {type(hasher).__name__}")
        except Exception as e:
            print(f"\n[3] 해시 알고리즘 정보 추출 실패: {e}")
        
        # 4. 비밀번호 검증 테스트
        print(f"\n[4] 비밀번호 검증 테스트:")
        is_valid = check_password(raw_password, hashed_password)
        print(f"    올바른 비밀번호 검증: {'✓ 성공' if is_valid else '✗ 실패'}")
        
        # 잘못된 비밀번호로 검증
        wrong_password = raw_password + "wrong"
        is_invalid = check_password(wrong_password, hashed_password)
        print(f"    잘못된 비밀번호 검증: {'✗ 실패 (정상)' if not is_invalid else '✓ 성공 (비정상)'}")
        
        # 5. 해시 형식 분석
        print(f"\n[5] 해시 형식 분석:")
        if hashed_password.startswith('pbkdf2_'):
            parts = hashed_password.split('$')
            if len(parts) >= 4:
                print(f"    알고리즘: {parts[0]}")
                print(f"    반복 횟수: {parts[1]}")
                print(f"    Salt: {parts[2][:20]}... (길이: {len(parts[2])})")
                print(f"    해시값: {parts[3][:20]}... (길이: {len(parts[3])})")
        elif hashed_password.startswith('argon2'):
            print(f"    알고리즘: Argon2")
            print(f"    형식: {hashed_password[:50]}...")
        else:
            print(f"    형식: {hashed_password[:50]}...")
        
        # 6. 동일한 비밀번호를 여러 번 해시화했을 때 결과 비교
        print(f"\n[6] 동일한 비밀번호 재해시화 테스트:")
        hashed_password_2 = make_password(raw_password)
        hashed_password_3 = make_password(raw_password)
        print(f"    첫 번째 해시: {hashed_password[:50]}...")
        print(f"    두 번째 해시: {hashed_password_2[:50]}...")
        print(f"    세 번째 해시: {hashed_password_3[:50]}...")
        print(f"    해시값이 다름 (Salt 사용): {'✓ 예' if hashed_password != hashed_password_2 else '✗ 아니오'}")
        print(f"    모두 올바른 비밀번호 검증: {'✓ 성공' if all([
            check_password(raw_password, hashed_password),
            check_password(raw_password, hashed_password_2),
            check_password(raw_password, hashed_password_3)
        ]) else '✗ 실패'}")

def test_database_storage():
    """데이터베이스에 실제 저장되는지 테스트"""
    print_separator("데이터베이스 저장 테스트")
    
    try:
        # 테스트용 관리자 생성 (실제로는 저장하지 않음)
        from django.contrib.auth.hashers import make_password
        
        test_password = "test_password_123"
        hashed_password = make_password(test_password)
        
        print(f"\n[1] 테스트 비밀번호:")
        print(f"    원본: {test_password}")
        print(f"    해시: {hashed_password}")
        
        # 실제 DB에 저장되는 형식 시뮬레이션
        print(f"\n[2] 데이터베이스 저장 형식:")
        print(f"    필드명: memberShipPassword")
        print(f"    타입: VARCHAR(255)")
        print(f"    저장값: {hashed_password}")
        print(f"    저장 길이: {len(hashed_password)} 문자")
        
        # AdminMemberShip 모델의 set_password 메서드 테스트
        print(f"\n[3] AdminMemberShip.set_password() 메서드 테스트:")
        admin_member = AdminMemberShip(
            memberShipId='test_user_' + str(hash(test_password))[-8:],
            memberShipName='테스트 사용자',
            memberShipEmail=f'test_{hash(test_password)}@test.com',
            memberShipPassword=hashed_password,  # 해시화된 비밀번호 직접 설정
        )
        print(f"    모델에 해시화된 비밀번호 설정 완료")
        print(f"    check_password('{test_password}', admin_member.memberShipPassword): {admin_member.check_password(test_password)}")
        print(f"    check_password('wrong', admin_member.memberShipPassword): {admin_member.check_password('wrong')}")
        
        # set_password 메서드 사용
        print(f"\n[4] set_password() 메서드 사용:")
        admin_member.set_password("new_password_456")
        print(f"    새로운 비밀번호로 변경 완료")
        print(f"    해시화된 비밀번호: {admin_member.memberShipPassword[:50]}...")
        print(f"    check_password('new_password_456', ...): {admin_member.check_password('new_password_456')}")
        print(f"    check_password('test_password_123', ...): {admin_member.check_password('test_password_123')}")
        
    except Exception as e:
        print(f"\n[오류] 데이터베이스 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_existing_admin_passwords():
    """기존 관리자 비밀번호 형식 확인"""
    print_separator("기존 관리자 비밀번호 형식 확인")
    
    try:
        admins = AdminMemberShip.objects.all()[:5]  # 최대 5명만
        
        if not admins.exists():
            print("\n[정보] 데이터베이스에 저장된 관리자가 없습니다.")
            return
        
        print(f"\n[1] 저장된 관리자 수: {admins.count()}명")
        
        for i, admin in enumerate(admins, 1):
            print(f"\n[관리자 {i}] {admin.memberShipName} ({admin.memberShipId})")
            print(f"    SID: {admin.memberShipSid}")
            print(f"    비밀번호 해시 길이: {len(admin.memberShipPassword)} 문자")
            print(f"    비밀번호 해시 형식: {admin.memberShipPassword[:50]}...")
            
            # 해시 알고리즘 추출
            if admin.memberShipPassword.startswith('pbkdf2_'):
                parts = admin.memberShipPassword.split('$')
                if len(parts) >= 4:
                    print(f"    알고리즘: {parts[0]}")
                    print(f"    반복 횟수: {parts[1]}")
            elif admin.memberShipPassword.startswith('argon2'):
                print(f"    알고리즘: Argon2")
            else:
                print(f"    알고리즘: 기타")
            
    except Exception as e:
        print(f"\n[오류] 기존 관리자 조회 실패: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 함수"""
    try:
        # 1. 비밀번호 해시화 테스트
        test_password_hashing()
        
        # 2. 데이터베이스 저장 테스트
        test_database_storage()
        
        # 3. 기존 관리자 비밀번호 확인
        test_existing_admin_passwords()
        
        print_separator("테스트 완료")
        print("\n[요약]")
        print("1. Django의 make_password() 함수가 비밀번호를 해시화합니다.")
        print("2. 해시화된 비밀번호는 데이터베이스에 VARCHAR(255)로 저장됩니다.")
        print("3. check_password() 함수로 원본 비밀번호와 해시를 비교합니다.")
        print("4. 동일한 비밀번호도 매번 다른 해시값이 생성됩니다 (Salt 사용).")
        print("5. 해시 알고리즘은 Django 설정에 따라 결정됩니다 (기본: PBKDF2).")
        
    except Exception as e:
        print(f"\n[치명적 오류] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()



