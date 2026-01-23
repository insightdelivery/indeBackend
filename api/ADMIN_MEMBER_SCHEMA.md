# 관리자 회원 DB 스키마 (AdminMemberShip)

## 테이블명
`adminMemberShip`

## 필드 구조

| 필드명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| **memberShipSid** | CHAR(15) | PRIMARY KEY, NOT NULL | 회원 고유 식별자 (시퀀스 코드) |
| **memberShipId** | VARCHAR(50) | UNIQUE, NOT NULL | 회원 ID (로그인용) |
| **memberShipPassword** | VARCHAR(255) | NOT NULL | 비밀번호 (해시화됨) |
| **memberShipName** | VARCHAR(100) | NOT NULL | 이름 |
| **memberShipEmail** | VARCHAR(255) | UNIQUE, NOT NULL | 이메일 주소 |
| **memberShipPhone** | VARCHAR(20) | NULL | 전화번호 |
| **memberShipLevel** | INTEGER | NOT NULL, DEFAULT=1 | 회원 레벨 (1~10) |
| **is_admin** | BOOLEAN | NOT NULL, DEFAULT=FALSE | 관리자 여부 |
| **is_active** | BOOLEAN | NOT NULL, DEFAULT=TRUE | 활성화 여부 |
| **last_login** | DATETIME | NULL | 마지막 로그인 시간 |
| **login_count** | INTEGER | NOT NULL, DEFAULT=0 | 로그인 횟수 |
| **created_at** | DATETIME | NOT NULL, AUTO | 생성일시 |
| **updated_at** | DATETIME | NOT NULL, AUTO | 수정일시 |

## 인덱스

- `memberShipId` (UNIQUE)
- `memberShipEmail` (UNIQUE)
- `is_active`, `is_admin` (복합 인덱스)
- `created_at` (정렬용)

## 주요 메서드

### `set_password(raw_password)`
비밀번호를 해시화하여 저장합니다.

### `check_password(raw_password)`
입력된 비밀번호가 일치하는지 확인합니다.

### `is_staff()`
스태프 여부를 반환합니다 (관리자 또는 레벨 5 이상).

## 사용 예시

```python
from api.models import AdminMemberShip

# 회원 생성
admin_member = AdminMemberShip.objects.create(
    memberShipId='admin01',
    memberShipName='관리자',
    memberShipEmail='admin@example.com',
    memberShipLevel=10,
    is_admin=True,
)
admin_member.set_password('password123')

# 비밀번호 확인
if admin_member.check_password('password123'):
    print('비밀번호 일치')

# 조회
admin = AdminMemberShip.objects.get(memberShipId='admin01')
```

## JWT 토큰 페이로드

```python
{
    'user_id': str(memberShipSid),  # 시퀀스 코드 (CHAR(15))
    'username': memberShipId,
    'email': memberShipEmail,
    'name': memberShipName,
    'level': memberShipLevel,
    'is_admin': is_admin,
    'site': 'admin_api',
    'token_type': 'access',
}
```

