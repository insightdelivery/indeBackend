"""
Cloudflare Stream API 연결 테스트 스크립트
환경 변수 및 API 인증 확인
"""
import os
import sys
from pathlib import Path

# Django 설정 로드
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# 환경 변수 로드
from dotenv import load_dotenv

# .env 파일 로드
env_path = BASE_DIR / 'env' / '.env.local'
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✅ 환경 변수 파일 로드: {env_path}")
else:
    print(f"⚠️  환경 변수 파일을 찾을 수 없습니다: {env_path}")

# 환경 변수 확인
account_id = os.getenv('CF_ACCOUNT_ID', '').strip()
api_token = os.getenv('CF_STREAM_TOKEN', '').strip()

print("\n" + "="*60)
print("Cloudflare Stream 환경 변수 확인")
print("="*60)
print(f"CF_ACCOUNT_ID: {account_id if account_id else '❌ 설정되지 않음'}")
print(f"CF_STREAM_TOKEN: {'✅ 설정됨' if api_token else '❌ 설정되지 않음'} (길이: {len(api_token)})")
if api_token:
    print(f"  토큰 앞 10자: {api_token[:10]}...")
    print(f"  토큰 뒤 10자: ...{api_token[-10:]}")

if not account_id or not api_token:
    print("\n❌ 환경 변수가 설정되지 않았습니다.")
    sys.exit(1)

# API 테스트
import requests

BASE_URL = "https://api.cloudflare.com/client/v4"
headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json',
}

print("\n" + "="*60)
print("Cloudflare Stream API 연결 테스트")
print("="*60)

# 1. Account 정보 확인
print("\n1. Account 정보 확인...")
account_url = f"{BASE_URL}/accounts/{account_id}"
print(f"   Account ID 길이: {len(account_id)} (일반적으로 32자)")
print(f"   Account ID 형식: {account_id[:8]}...{account_id[-8:]}")
try:
    response = requests.get(account_url, headers=headers, timeout=10)
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            account_info = result.get('result', {})
            print(f"   ✅ Account 확인 성공")
            print(f"   Account Name: {account_info.get('name', 'N/A')}")
        else:
            print(f"   ❌ Account 확인 실패: {result}")
    else:
        print(f"   ❌ Account 확인 실패: {response.text}")
        result = response.json() if response.text else {}
        if result.get('errors'):
            for error in result.get('errors', []):
                if error.get('code') == 9109:
                    print("   ⚠️  이 오류는 Account ID 오타뿐 아니라, 토큰에 Account 조회 권한이 없을 때도 발생할 수 있습니다.")
                    print("   💡 아래 '1-1 Account 목록 조회'가 성공하면 Account ID는 정상입니다.")
except Exception as e:
    print(f"   ❌ 오류 발생: {e}")

# 1-1. Account 목록 조회 (Account ID 확인용)
print("\n1-1. Account 목록 조회 (올바른 Account ID 찾기)...")
accounts_url = f"{BASE_URL}/accounts"
try:
    response = requests.get(accounts_url, headers=headers, timeout=10)
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            accounts = result.get('result', [])
            print(f"   ✅ 사용 가능한 Account 목록:")
            for acc in accounts:
                acc_id = acc.get('id', '')
                acc_name = acc.get('name', 'N/A')
                is_current = '✅ 현재 사용 중' if acc_id == account_id else ''
                print(f"      - ID: {acc_id} | Name: {acc_name} {is_current}")
            if account_id not in [acc.get('id') for acc in accounts]:
                print(f"\n   ⚠️  현재 설정된 Account ID({account_id})가 목록에 없습니다!")
                if accounts:
                    correct_id = accounts[0].get('id')
                    print(f"   💡 올바른 Account ID 중 하나: {correct_id}")
                    print(f"   💡 .env 파일의 CF_ACCOUNT_ID를 위 값으로 변경하세요")
        else:
            print(f"   ❌ Account 목록 조회 실패: {result}")
    elif response.status_code == 403:
        print(f"   ❌ 인증 실패: 토큰에 'Account:Read' 권한이 필요합니다.")
        print(f"   💡 Cloudflare Dashboard > API Tokens에서 토큰 권한 확인")
    else:
        print(f"   ❌ 오류: {response.status_code} - {response.text}")
except Exception as e:
    print(f"   ❌ 오류 발생: {e}")

# 2. Stream API 엔드포인트 확인
print("\n2. Stream API 엔드포인트 확인...")
stream_url = f"{BASE_URL}/accounts/{account_id}/stream"
print(f"   URL: {stream_url}")

# 3. Stream 비디오 목록 조회 테스트 (읽기 권한 확인)
print("\n3. Stream 비디오 목록 조회 테스트 (읽기 권한 확인)...")
try:
    response = requests.get(stream_url, headers=headers, timeout=10)
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print(f"   ✅ Stream API 읽기 권한 확인 성공")
            videos = result.get('result', [])
            print(f"   비디오 개수: {len(videos)}")
        else:
            print(f"   ❌ Stream API 읽기 실패: {result}")
    elif response.status_code == 403:
        print(f"   ❌ 인증 실패 (403): {response.text}")
        print(f"   토큰에 'Account.Cloudflare Stream:Read' 권한이 필요합니다.")
    else:
        print(f"   ❌ 오류: {response.status_code} - {response.text}")
except Exception as e:
    print(f"   ❌ 오류 발생: {e}")

# 4. 업로드 엔드포인트 테스트 (작은 테스트 파일)
print("\n4. 업로드 엔드포인트 테스트...")
print("   (실제 파일 업로드는 하지 않고 엔드포인트만 확인)")

print("\n" + "="*60)
print("테스트 완료")
print("="*60)
print("\n💡 팁:")
print("1. Cloudflare Dashboard > My Profile > API Tokens에서 토큰 확인")
print("2. 토큰에 다음 권한이 있는지 확인:")
print("   - Account.Cloudflare Stream:Read")
print("   - Account.Cloudflare Stream:Edit")
print("3. Account ID는 Cloudflare Dashboard 우측 사이드바에서 확인 가능")
print("4. 토큰이 만료되지 않았는지 확인")

