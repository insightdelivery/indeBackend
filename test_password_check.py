#!/usr/bin/env python
"""
비밀번호 검증 테스트 프로그램
특정 관리자의 비밀번호가 올바르게 저장되고 검증되는지 확인합니다.
"""
import os
import sys
import django

# Django 설정 로드
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from api.models import AdminMemberShip
from django.contrib.auth.hashers import make_password, check_password

def test_admin_password(member_ship_id, test_password):
    """특정 관리자의 비밀번호 검증 테스트"""
    print(f"\n{'='*60}")
    print(f"관리자 비밀번호 검증 테스트")
    print('='*60)
    
    try:
        # 관리자 조회
        admin = AdminMemberShip.objects.get(memberShipId=member_ship_id)
        
        print(f"\n[1] 관리자 정보:")
        print(f"    SID: {admin.memberShipSid}")
        print(f"    ID: {admin.memberShipId}")
        print(f"    이름: {admin.memberShipName}")
        print(f"    이메일: {admin.memberShipEmail}")
        print(f"    활성화: {admin.is_active}")
        
        print(f"\n[2] 비밀번호 정보:")
        print(f"    입력한 비밀번호: '{test_password}'")
        print(f"    입력한 비밀번호 길이: {len(test_password)} 문자")
        
        # DB에 저장된 비밀번호 해시 확인
        stored_password = admin.memberShipPassword
        print(f"\n[3] DB에 저장된 비밀번호 해시:")
        if not stored_password or stored_password.strip() == '':
            print(f"    ❌ 비밀번호가 저장되지 않았습니다! (NULL 또는 빈 문자열)")
            return False
        
        print(f"    해시 길이: {len(stored_password)} 문자")
        print(f"    해시 형식: {stored_password[:80]}...")
        print(f"    해시 전체: {stored_password}")
        
        # 해시 알고리즘 확인
        if stored_password.startswith('pbkdf2_'):
            parts = stored_password.split('$')
            if len(parts) >= 4:
                print(f"    알고리즘: {parts[0]}")
                print(f"    반복 횟수: {parts[1]}")
                print(f"    Salt: {parts[2][:30]}...")
        elif stored_password.startswith('argon2'):
            print(f"    알고리즘: Argon2")
        else:
            print(f"    ⚠️  알 수 없는 해시 형식입니다!")
        
        # 비밀번호 검증 테스트
        print(f"\n[4] 비밀번호 검증 테스트:")
        
        # 방법 1: 모델의 check_password 메서드 사용
        result1 = admin.check_password(test_password)
        print(f"    admin.check_password('{test_password}'): {result1}")
        
        # 방법 2: Django의 check_password 직접 사용
        result2 = check_password(test_password, stored_password)
        print(f"    check_password('{test_password}', stored_hash): {result2}")
        
        # 잘못된 비밀번호로 테스트
        wrong_result = admin.check_password(test_password + "wrong")
        print(f"    admin.check_password('{test_password}wrong'): {wrong_result} (잘못된 비밀번호)")
        
        if result1 and result2:
            print(f"\n    ✅ 비밀번호가 올바르게 저장되고 검증됩니다!")
            return True
        else:
            print(f"\n    ❌ 비밀번호 검증 실패!")
            
            # 추가 진단
            print(f"\n[5] 추가 진단:")
            
            # 비밀번호를 새로 해시화해서 비교
            new_hash = make_password(test_password)
            print(f"    입력한 비밀번호를 새로 해시화: {new_hash[:80]}...")
            print(f"    새 해시로 검증: {check_password(test_password, new_hash)}")
            
            # 저장된 해시와 새 해시 비교
            if stored_password == new_hash:
                print(f"    ⚠️  저장된 해시와 새 해시가 동일합니다 (Salt가 없을 수 있음)")
            else:
                print(f"    ✓ 저장된 해시와 새 해시가 다릅니다 (정상, Salt 사용)")
            
            return False
            
    except AdminMemberShip.DoesNotExist:
        print(f"\n❌ 관리자를 찾을 수 없습니다: {member_ship_id}")
        print(f"\n사용 가능한 관리자 목록:")
        admins = AdminMemberShip.objects.all()[:10]
        for admin in admins:
            print(f"    - {admin.memberShipId} ({admin.memberShipName})")
        return False
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 함수"""
    print("="*60)
    print("비밀번호 검증 테스트 프로그램")
    print("="*60)
    
    # 명령줄 인자 확인
    if len(sys.argv) >= 3:
        member_ship_id = sys.argv[1]
        test_password = sys.argv[2]
    else:
        # 대화형 입력
        print("\n테스트할 관리자 정보를 입력하세요:")
        member_ship_id = input("관리자 ID (memberShipId): ").strip()
        test_password = input("비밀번호: ").strip()
    
    if not member_ship_id or not test_password:
        print("\n❌ 관리자 ID와 비밀번호를 모두 입력해주세요.")
        print("\n사용법:")
        print("  python3 test_password_check.py <memberShipId> <password>")
        print("\n또는:")
        print("  python3 test_password_check.py")
        print("  (대화형으로 입력)")
        sys.exit(1)
    
    # 테스트 실행
    success = test_admin_password(member_ship_id, test_password)
    
    if success:
        print("\n" + "="*60)
        print("✅ 테스트 성공: 비밀번호가 올바르게 작동합니다.")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("❌ 테스트 실패: 비밀번호 검증에 문제가 있습니다.")
        print("="*60)
        sys.exit(1)

if __name__ == '__main__':
    main()



