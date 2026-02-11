# AWS S3 설정 가이드

## 필요한 환경 변수

### 필수 환경 변수

1. **AWS_ACCESS_KEY_ID**
   - AWS IAM 사용자의 Access Key ID
   - AWS 콘솔 > IAM > 사용자 > 보안 자격 증명에서 생성

2. **AWS_SECRET_ACCESS_KEY**
   - AWS IAM 사용자의 Secret Access Key
   - Access Key ID와 함께 생성됨

3. **AWS_S3_REGION_NAME**
   - S3 버킷이 위치한 리전
   - 기본값: `ap-northeast-2` (서울)
   - 예: `us-east-1`, `ap-northeast-2`

### 환경별 버킷 설정

4. **AWS_STORAGE_BUCKET_NAME_DEVELOPMENT**
   - Local/Development 환경에서 사용할 버킷 이름
   - 기본값: `inde-develope`

5. **AWS_STORAGE_BUCKET_NAME_PRODUCTION**
   - Production 환경에서 사용할 버킷 이름
   - 기본값: `inde-production`

6. **AWS_STORAGE_BUCKET_NAME** (선택)
   - 명시적으로 버킷 이름을 지정할 경우
   - 환경별 자동 선택보다 우선 적용

### 선택적 환경 변수

7. **AWS_S3_CUSTOM_DOMAIN** (선택)
   - CloudFront 또는 커스텀 도메인
   - 예: `cdn.inde.kr`
   - 설정 시 S3 URL 대신 커스텀 도메인 사용

## 환경 변수 설정 방법

### Local 환경 (env/local/.env)

```env
# AWS S3 설정
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_S3_REGION_NAME=ap-northeast-2

# Development 버킷 (Local에서는 inde-develope 사용)
AWS_STORAGE_BUCKET_NAME_DEVELOPMENT=inde-develope
AWS_STORAGE_BUCKET_NAME_PRODUCTION=inde-production
```

### Production 환경 (env/.env.production)

```env
# AWS S3 설정
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_S3_REGION_NAME=ap-northeast-2

# Production 버킷 (Production에서는 inde-production 사용)
AWS_STORAGE_BUCKET_NAME_DEVELOPMENT=inde-develope
AWS_STORAGE_BUCKET_NAME_PRODUCTION=inde-production

# CloudFront 도메인 (선택)
AWS_S3_CUSTOM_DOMAIN=cdn.inde.kr
```

## 버킷 자동 선택 로직

1. `AWS_STORAGE_BUCKET_NAME`이 명시적으로 설정된 경우 → 해당 버킷 사용
2. `DJANGO_DEBUG=0` 또는 `DEBUG=False`인 경우 → `inde-production` 사용
3. 그 외의 경우 → `inde-develope` 사용

## AWS IAM 권한 설정

S3 접근을 위한 최소 IAM 정책:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:HeadObject"
            ],
            "Resource": [
                "arn:aws:s3:::inde-develope/*",
                "arn:aws:s3:::inde-production/*",
                "arn:aws:s3:::inde-develope",
                "arn:aws:s3:::inde-production"
            ]
        }
    ]
}
```

## API 엔드포인트

### 파일 업로드
- **POST** `/admin-api/files/upload/`
- 요청: `multipart/form-data` (file, folder, prefix)
- 응답: `{ url, key, filename, original_filename, size, content_type }`

### 파일 삭제
- **DELETE** `/admin-api/files/delete/`
- 요청: `{ key }` 또는 `{ url }`
- 응답: `{ message }`

### 파일 정보 조회
- **GET** `/admin-api/files/info/?key=...` 또는 `?url=...`
- 응답: `{ key, url, size, content_type, last_modified, exists }`

### 파일 목록 조회
- **GET** `/admin-api/files/list/?prefix=uploads/&max_keys=1000`
- 응답: `{ files: [...], count: ... }`

## 사용 예제

### Python에서 사용

```python
from core.s3_storage import get_s3_storage

s3 = get_s3_storage()

# 파일 업로드
with open('image.jpg', 'rb') as f:
    url = s3.upload_file(f, 'images/2024/01/image.jpg', 'image/jpeg')

# 파일 삭제
s3.delete_file('images/2024/01/image.jpg')

# 파일 정보 조회
info = s3.get_file_info('images/2024/01/image.jpg')

# 파일 URL 가져오기
url = s3.get_file_url('images/2024/01/image.jpg')
```

