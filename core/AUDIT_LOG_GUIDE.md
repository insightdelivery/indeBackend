# audit_log 테이블 역할 및 사용 가이드

## 📋 audit_log 테이블의 역할

`audit_log` 테이블은 **사용자 활동 감사 로그(Audit Log)**를 저장하는 테이블입니다. 시스템의 모든 중요한 사용자 활동을 기록하여 보안, 추적, 분석을 가능하게 합니다.

### 주요 역할

1. **보안 감사 (Security Audit)**
   - 로그인/로그아웃 시도 기록
   - 실패한 로그인 시도 추적
   - 의심스러운 활동 탐지

2. **사용자 활동 추적 (User Activity Tracking)**
   - CRUD 작업 기록 (생성, 조회, 수정, 삭제)
   - 어떤 사용자가 언제 무엇을 했는지 기록

3. **컴플라이언스 (Compliance)**
   - 법적 요구사항 충족
   - 데이터 변경 이력 관리
   - 감사 증거 자료 제공

4. **문제 해결 (Troubleshooting)**
   - 오류 발생 시 원인 분석
   - 사용자 문의 대응
   - 시스템 이슈 디버깅

## 📊 테이블 구조

### 필드 설명

| 필드명 | 타입 | 설명 |
|--------|------|------|
| `id` | BigAutoField | 고유 식별자 (자동 증가) |
| `user` | ForeignKey (Account) | 사용자 (Account 모델 참조, NULL 가능) |
| `site_slug` | CharField(50) | 사이트 식별자 (admin_api, public_api 등) |
| `action` | CharField(20) | 액션 타입 (login, logout, create, read, update, delete) |
| `resource` | CharField(100) | 리소스 타입 (account, adminMemberShip 등) |
| `resource_id` | CharField(100) | 리소스 ID (대상 객체의 ID) |
| `ip_address` | GenericIPAddressField | 클라이언트 IP 주소 |
| `user_agent` | TextField | 브라우저/클라이언트 정보 |
| `details` | JSONField | 상세 정보 (JSON 형식) |
| `created_at` | DateTimeField | 로그 생성 시간 |

### 액션 타입 (ACTION_CHOICES)

- `login`: 로그인
- `logout`: 로그아웃
- `create`: 생성
- `read`: 조회
- `update`: 수정
- `delete`: 삭제

## 🔍 사용 예시

### 1. 로그인 성공 기록

```python
AuditLog.objects.create(
    user=user,
    site_slug='admin_api',
    action='login',
    resource='account',
    resource_id=str(user.id),
    ip_address='192.168.1.100',
    user_agent='Mozilla/5.0...',
    details={'status': 'success'}
)
```

### 2. 로그인 실패 기록

```python
AuditLog.objects.create(
    user=user,
    site_slug='admin_api',
    action='login',
    resource='account',
    resource_id=str(user.id),
    ip_address='192.168.1.100',
    user_agent='Mozilla/5.0...',
    details={'status': 'failed', 'reason': 'invalid_password'}
)
```

### 3. 데이터 생성 기록

```python
AuditLog.objects.create(
    user=request.user,
    site_slug='admin_api',
    action='create',
    resource='adminMemberShip',
    resource_id=str(new_member.memberShipSid),
    ip_address=self.get_client_ip(request),
    user_agent=request.META.get('HTTP_USER_AGENT', ''),
    details={
        'memberShipId': new_member.memberShipId,
        'memberShipName': new_member.memberShipName,
    }
)
```

### 4. 데이터 수정 기록

```python
AuditLog.objects.create(
    user=request.user,
    site_slug='admin_api',
    action='update',
    resource='adminMemberShip',
    resource_id=str(member.memberShipSid),
    ip_address=self.get_client_ip(request),
    user_agent=request.META.get('HTTP_USER_AGENT', ''),
    details={
        'changed_fields': ['memberShipName', 'memberShipLevel'],
        'old_values': {'memberShipName': '이전이름', 'memberShipLevel': 1},
        'new_values': {'memberShipName': '새이름', 'memberShipLevel': 5},
    }
)
```

## 📈 조회 예시

### 1. 특정 사용자의 로그인 기록 조회

```python
login_logs = AuditLog.objects.filter(
    user=user,
    action='login',
    site_slug='admin_api'
).order_by('-created_at')
```

### 2. 실패한 로그인 시도 조회

```python
failed_logins = AuditLog.objects.filter(
    action='login',
    details__status='failed'
).order_by('-created_at')
```

### 3. 특정 리소스의 변경 이력 조회

```python
resource_history = AuditLog.objects.filter(
    resource='adminMemberShip',
    resource_id='uuid-here'
).order_by('created_at')
```

### 4. 특정 기간의 활동 조회

```python
from datetime import datetime, timedelta

recent_activity = AuditLog.objects.filter(
    created_at__gte=datetime.now() - timedelta(days=7)
).order_by('-created_at')
```

## 🛡️ 보안 활용

### 1. 의심스러운 활동 탐지

```python
# 짧은 시간 내 여러 번 실패한 로그인 시도
suspicious_logins = AuditLog.objects.filter(
    action='login',
    details__status='failed',
    created_at__gte=datetime.now() - timedelta(minutes=5)
).values('ip_address').annotate(
    count=Count('id')
).filter(count__gte=5)
```

### 2. IP 주소 기반 추적

```python
# 특정 IP에서의 모든 활동
ip_activity = AuditLog.objects.filter(
    ip_address='192.168.1.100'
).order_by('-created_at')
```

## 📝 주의사항

1. **데이터 보관**: 오래된 로그는 정기적으로 아카이브하거나 삭제
2. **성능**: 대량의 로그 데이터는 인덱스 최적화 필요
3. **개인정보**: IP 주소, User Agent 등은 개인정보에 해당할 수 있음
4. **저장 공간**: 로그가 계속 쌓이므로 저장 공간 관리 필요

## 🔧 인덱스

현재 설정된 인덱스:
- `user + created_at`: 사용자별 활동 조회 최적화
- `site_slug + action + created_at`: 사이트별 액션별 조회 최적화

## 💡 활용 시나리오

1. **보안 모니터링**: 실패한 로그인 시도 모니터링
2. **사용자 행동 분석**: 어떤 기능을 많이 사용하는지 분석
3. **오류 추적**: 문제 발생 시 로그를 통해 원인 파악
4. **컴플라이언스**: 법적 요구사항 충족을 위한 활동 기록
5. **감사 (Audit)**: 외부 감사 시 증거 자료 제공

