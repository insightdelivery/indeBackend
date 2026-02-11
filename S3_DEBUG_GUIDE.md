# S3 프로덕션 디버깅 가이드

## 프로덕션 서버에서 S3 설정 확인하기

### 1. 올바른 경로로 이동

프로덕션 서버에서 `manage.py`가 있는 디렉토리로 이동해야 합니다.

```bash
# 프로젝트 루트로 이동 (manage.py가 있는 디렉토리)
cd /home/ubuntu/inde_api  # 또는 실제 프로젝트 루트 경로
# 또는
cd /home/ubuntu/inde_api/backend  # backend 디렉토리가 루트인 경우

# manage.py 파일 확인
ls -la manage.py
```

### 2. S3 설정 확인 명령어 실행

```bash
# 프로덕션 설정으로 실행
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py check_s3_config
```

또는 가상환경이 활성화되어 있다면:

```bash
# 가상환경 활성화 (필요한 경우)
source venv/bin/activate  # 또는 .venv/bin/activate

# 명령어 실행
python manage.py check_s3_config
```

### 3. 환경 변수 확인

프로덕션 환경 변수가 제대로 로드되는지 확인:

```bash
# .env.production 파일 확인
cat env/.env.production | grep AWS

# 또는 환경 변수 직접 확인
echo $DJANGO_DEBUG
echo $AWS_STORAGE_BUCKET_NAME_PRODUCTION
```

### 4. 가능한 문제점들

#### 문제 1: DJANGO_DEBUG 환경 변수 미설정
- **증상**: 개발 버킷(`inde-develope`)을 사용함
- **해결**: `.env.production`에 `DJANGO_DEBUG=0` 설정

#### 문제 2: 버킷 이름 환경 변수 미설정
- **증상**: 기본값(`inde-production`)을 사용하지만 실제 버킷 이름이 다를 수 있음
- **해결**: `.env.production`에 `AWS_STORAGE_BUCKET_NAME_PRODUCTION=inde-production` 명시

#### 문제 3: IAM 권한 부족
- **증상**: `AccessDenied` 또는 `403 Forbidden` 에러
- **해결**: IAM 사용자에게 `inde-production` 버킷에 대한 `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` 권한 부여

#### 문제 4: 버킷이 존재하지 않음
- **증상**: `NoSuchBucket` 에러
- **해결**: AWS 콘솔에서 `inde-production` 버킷 생성 확인

### 5. 로그 확인

Django 로그에서 S3 관련 메시지 확인:

```bash
# 로그 파일 위치 확인 (systemd를 사용하는 경우)
journalctl -u your-django-service -f | grep S3

# 또는 로그 파일 직접 확인
tail -f /path/to/django/logs/*.log | grep -i s3
```

로그에서 확인할 메시지:
- `S3 Storage 초기화 완료 - 버킷: inde-production, 리전: ap-northeast-2`
- `S3 업로드 시도 - 버킷: inde-production, 키: ...`
- `S3 업로드 실패 - 버킷: ..., 에러 코드: ..., 메시지: ...`

### 6. 빠른 테스트

간단한 업로드 테스트:

```bash
python manage.py test_s3
```

이 명령어는 실제로 파일을 업로드하고 삭제하여 전체 프로세스를 테스트합니다.

