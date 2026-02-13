# 아티클(Article) 백엔드 API 문서

## 📋 목차

1. [개요](#개요)
2. [프로젝트 구조](#프로젝트-구조)
3. [데이터베이스 모델](#데이터베이스-모델)
4. [API 엔드포인트](#api-엔드포인트)
5. [시리얼라이저](#시리얼라이저)
6. [이미지 처리 로직 (S3)](#이미지-처리-로직-s3)
7. [주요 비즈니스 로직](#주요-비즈니스-로직)
8. [에러 처리](#에러-처리)
9. [로깅](#로깅)

---

## 개요

아티클 관리 시스템은 Django REST Framework를 기반으로 구현된 CRUD API입니다. 주요 기능은 다음과 같습니다:

- **아티클 생성/조회/수정/삭제**: 기본 CRUD 작업
- **이미지 관리**: 본문 및 썸네일 이미지를 AWS S3에 저장하고 Presigned URL로 제공
- **소프트 삭제**: 삭제된 아티클을 복구 가능하도록 보관
- **페이지네이션 및 필터링**: 목록 조회 시 다양한 필터 옵션 제공
- **일괄 작업**: 여러 아티클의 상태 변경 및 삭제

---

## 프로젝트 구조

```
backend/sites/admin_api/articles/
├── __init__.py
├── apps.py                    # Django 앱 설정
├── models.py                  # Article 모델 정의
├── serializers.py             # DRF 시리얼라이저 (검증 및 직렬화)
├── views.py                   # API 뷰 (비즈니스 로직)
├── utils.py                   # 이미지 처리 유틸리티 함수
├── urls.py                    # URL 라우팅
├── migrations/                # 데이터베이스 마이그레이션
├── CREATE_TABLE.sql           # 테이블 생성 SQL
├── ALTER_CONTENT_TO_MEDIUMTEXT.sql  # content 컬럼 타입 변경 SQL
└── README.md                  # 이 문서
```

### 파일별 역할

- **models.py**: `Article` 모델 정의 및 데이터베이스 스키마
- **serializers.py**: 요청/응답 데이터 검증 및 직렬화
- **views.py**: API 엔드포인트 구현 및 비즈니스 로직
- **utils.py**: 이미지 처리, S3 업로드/삭제, Presigned URL 생성 등 유틸리티 함수
- **urls.py**: URL 패턴 정의 및 뷰 매핑

---

## 데이터베이스 모델

### Article 모델

**테이블명**: `article`

#### 필드 구조

| 필드명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | AutoField | 아티클 ID (PK) | Primary Key |
| `title` | CharField(500) | 제목 | 필수 |
| `subtitle` | CharField(500) | 부제목 | 선택 |
| `content` | TextField | 본문 내용 (MEDIUMTEXT) | 필수 |
| `thumbnail` | CharField(500) | 썸네일 URL | 선택 |
| `category` | CharField(50) | 카테고리 (sysCodeSid) | 필수 |
| `author` | CharField(100) | 작성자 | 필수 |
| `authorAffiliation` | CharField(200) | 작성자 소속 | 선택 |
| `visibility` | CharField(50) | 공개 범위 (sysCodeSid) | 필수 |
| `status` | CharField(50) | 발행 상태 (sysCodeSid) | 기본값: 'draft' |
| `isEditorPick` | BooleanField | 에디터 추천 | 기본값: False |
| `viewCount` | IntegerField | 조회수 | 기본값: 0 |
| `rating` | FloatField | 평점 | 선택 |
| `commentCount` | IntegerField | 댓글 수 | 기본값: 0 |
| `highlightCount` | IntegerField | 하이라이트 수 | 기본값: 0 |
| `questionCount` | IntegerField | 질문 수 | 기본값: 0 |
| `tags` | JSONField | 태그 목록 | 기본값: [] |
| `questions` | JSONField | 질문 목록 | 기본값: [] |
| `previewLength` | IntegerField | 미리보기 길이 | 기본값: 50 |
| `scheduledAt` | DateTimeField | 예약 발행 일시 | 선택 |
| `deletedAt` | DateTimeField | 삭제 일시 | 선택 (소프트 삭제) |
| `deletedBy` | CharField(100) | 삭제자 | 선택 |
| `createdAt` | DateTimeField | 생성 일시 | 자동 생성 |
| `updatedAt` | DateTimeField | 수정 일시 | 자동 업데이트 |

#### 인덱스

- `idx_article_category`: `category` 필드
- `idx_article_status`: `status` 필드
- `idx_article_visibility`: `visibility` 필드
- `idx_article_created`: `createdAt` 필드
- `idx_article_deleted`: `deletedAt` 필드
- `idx_article_author`: `author` 필드

#### 모델 메서드

- `soft_delete(deleted_by=None)`: 소프트 삭제 (status='deleted', deletedAt 설정)
- `restore()`: 삭제된 아티클 복구
- `is_deleted` (property): 삭제 여부 확인

#### 중요 사항

- **content 필드**: MySQL `MEDIUMTEXT` 타입 (최대 약 16MB)으로 변경됨
  - 이유: 본문에 이미지가 base64로 포함될 경우 용량이 커질 수 있음
  - 변경 SQL: `ALTER_CONTENT_TO_MEDIUMTEXT.sql` 참고

---

## API 엔드포인트

### 인증

모든 API는 `AdminJWTAuthentication`을 사용하며, `IsAuthenticated` 권한이 필요합니다.

### 엔드포인트 목록

#### 1. 아티클 목록 조회

```
GET /article/list
GET /article/list/
```

**Query Parameters:**
- `page` (int): 페이지 번호 (기본값: 1)
- `pageSize` (int): 페이지 크기 (기본값: 20)
- `startDate` (string): 시작 날짜 (YYYY-MM-DD)
- `endDate` (string): 종료 날짜 (YYYY-MM-DD)
- `category` (string): 카테고리 (sysCodeSid)
- `visibility` (string): 공개 범위 (sysCodeSid)
- `status` (string): 발행 상태 (sysCodeSid, 'deleted' 포함)
- `search` (string): 검색어 (제목, 본문, 작성자, 부제목)

**응답 예시:**
```json
{
  "IndeAPIResponse": {
    "Success": true,
    "Data": {
      "articles": [...],
      "total": 100,
      "page": 1,
      "pageSize": 20
    },
    "Message": "아티클 목록 조회 성공"
  }
}
```

**특징:**
- `status='deleted'`인 경우 `deletedAt__isnull=False`로 필터링하여 삭제된 항목만 조회
- 그 외의 경우 `deletedAt__isnull=True`로 필터링하여 삭제되지 않은 항목만 조회
- 각 아티클의 썸네일은 Presigned URL로 변환되어 반환됨

---

#### 2. 아티클 상세 조회

```
GET /article/{id}
GET /article/{id}/
```

**응답:**
- 본문의 S3 이미지 URL은 Presigned URL로 변환됨
- 썸네일 URL도 Presigned URL로 변환됨

---

#### 3. 아티클 생성

```
POST /article/create
POST /article/create/
```

**Request Body:**
```json
{
  "title": "제목",
  "subtitle": "부제목",
  "content": "<p>본문 내용...</p><img src=\"data:image/jpeg;base64,...\">",
  "thumbnail": "data:image/jpeg;base64,..." 또는 "https://...",
  "category": "SYS26209B002",
  "author": "작성자",
  "visibility": "SYS26209B015",
  "status": "SYS26209B020",
  "tags": ["태그1", "태그2"],
  "questions": ["질문1", "질문2"],
  "scheduledAt": "2026-02-11T12:00:00Z"
}
```

**처리 흐름:**
1. 시리얼라이저로 데이터 검증
2. 아티클 생성 (임시로 ID 획득)
3. 본문의 base64 이미지를 S3에 업로드하고 URL로 교체
4. 썸네일이 base64인 경우 S3에 업로드하고 URL로 교체
5. 응답 시 Presigned URL로 변환하여 반환

---

#### 4. 아티클 수정

```
PUT /article/{id}
PUT /article/{id}/
```

**Request Body:** (생성과 동일한 구조, 일부 필드만 전송 가능)

**처리 흐름:**
1. 기존 아티클 조회
2. 기존 이미지 키 추출 (나중에 삭제하기 위해)
3. 시리얼라이저로 데이터 검증 및 저장
4. 본문이 변경된 경우:
   - base64 이미지를 S3에 업로드하고 URL로 교체
   - 사용되지 않는 기존 이미지 삭제
5. 썸네일이 변경된 경우:
   - base64인 경우 S3에 업로드
   - URL인 경우 기존 URL과 비교하여 다를 때만 업데이트
   - 기존 썸네일과 새 썸네일의 키가 다를 때만 기존 썸네일 삭제
6. 응답 시 Presigned URL로 변환하여 반환

**중요:**
- 썸네일은 `request.data`에 `'thumbnail'` 키가 명시적으로 있을 때만 처리됨
- 썸네일이 변경되지 않았으면 업데이트하지 않음 (프론트엔드에서 명시적으로 보낸 경우에만 처리)

---

#### 5. 아티클 삭제 (소프트 삭제)

```
DELETE /article/{id}
DELETE /article/{id}/
```

**처리:**
- `soft_delete()` 메서드 호출
- `status='deleted'`, `deletedAt` 설정, `deletedBy` 설정
- 실제 데이터는 삭제되지 않음

---

#### 6. 아티클 일괄 삭제

```
DELETE /article/batch-delete
DELETE /article/batch-delete/
```

**Request Body:**
```json
{
  "ids": [1, 2, 3, ...]
}
```

**처리:**
- 각 아티클에 대해 소프트 삭제 수행
- 관련 이미지도 S3에서 삭제 (`delete_article_images()`)

---

#### 7. 아티클 상태 일괄 변경

```
PUT /article/batch-status
PUT /article/batch-status/
```

**Request Body:**
```json
{
  "ids": [1, 2, 3, ...],
  "status": "published"
}
```

---

#### 8. 아티클 복구

```
POST /article/{id}/restore
POST /article/{id}/restore/
```

**처리:**
- `restore()` 메서드 호출
- `status='draft'`, `deletedAt=None`, `deletedBy=None`으로 복구

---

#### 9. 아티클 영구 삭제

```
DELETE /article/{id}/hard-delete
DELETE /article/{id}/hard-delete/
```

**처리:**
- 관련 이미지를 S3에서 삭제
- 데이터베이스에서 완전히 삭제 (`article.delete()`)

---

#### 10. 아티클 엑셀 다운로드

```
GET /article/export
GET /article/export/
```

**Query Parameters:** (목록 조회와 동일)

**응답:**
- JSON 형식으로 반환 (프론트엔드에서 엑셀 변환)

---

## 시리얼라이저

### ArticleSerializer

전체 필드를 포함하는 기본 시리얼라이저입니다.

**Read-only 필드:**
- `id`, `viewCount`, `commentCount`, `highlightCount`, `questionCount`, `createdAt`, `updatedAt`

**검증:**
- `title`, `content`, `category`, `author`: 필수 필드, 공백 제거

---

### ArticleListSerializer

목록 조회용 간소화된 시리얼라이저입니다.

**포함 필드:**
- `content` 필드 제외 (용량 절감)
- `deletedAt`, `deletedBy` 포함 (휴지통 표시용)

---

### ArticleCreateSerializer

아티클 생성용 시리얼라이저입니다.

**검증:**
- `thumbnail`: base64 데이터인 경우 길이 검증 건너뛰기 (S3 업로드 예정)
- URL인 경우만 500자 제한 검증

---

### ArticleUpdateSerializer

아티클 수정용 시리얼라이저입니다.

**특징:**
- `partial=True` 지원 (일부 필드만 업데이트 가능)
- `title`, `content`, `category`, `author`: `required=False` (수정 시 선택적)
- `thumbnail`: base64 데이터인 경우 길이 검증 건너뛰기
- `visibility`, `status`: 빈 문자열 검증 추가

---

## 이미지 처리 로직 (S3)

### 이미지 저장 경로

```
article/YYYY/MM/{article_id}/{filename}
```

**예시:**
- 본문 이미지: `article/2026/02/3/image_0.jpeg`
- 썸네일: `article/2026/02/3/thumbnail.jpeg`

---

### 주요 유틸리티 함수

#### 1. `get_article_image_path(article_id, filename=None)`

아티클 이미지 저장 경로를 생성합니다.

---

#### 2. `extract_base64_images(html_content)`

HTML 본문에서 base64 이미지를 추출합니다.

**반환값:**
```python
[(full_tag, base64_data, extension), ...]
```

---

#### 3. `upload_base64_image_to_s3(base64_data, extension, article_id, image_type, image_index)`

base64 이미지를 S3에 업로드합니다.

**파라미터:**
- `image_type`: 'content' 또는 'thumbnail'
- `image_index`: 본문 내 여러 이미지 구분용 (0부터 시작)

**파일명 규칙:**
- 썸네일: `thumbnail.{extension}`
- 본문 이미지: `image_{index}.{extension}`

---

#### 4. `replace_base64_images_with_s3_urls(html_content, article_id)`

HTML 본문의 base64 이미지를 S3 URL로 교체합니다.

**반환값:**
```python
(new_content, uploaded_keys)
```

**처리:**
1. base64 이미지 추출
2. 각 이미지를 S3에 업로드
3. `<img src="data:image/...">` → `<img src="https://...s3...">`로 교체
4. 업로드된 S3 키 리스트 반환

---

#### 5. `upload_thumbnail_to_s3(thumbnail_data, article_id)`

썸네일을 S3에 업로드합니다.

**처리:**
- base64 데이터인 경우: S3에 업로드하고 URL 반환
- URL인 경우: 그대로 반환 (500자 제한)

---

#### 6. `delete_article_images(article_id)`

아티클 관련 모든 이미지를 S3에서 삭제합니다.

**처리:**
1. `article/YYYY/MM/{article_id}/` 경로의 모든 파일 목록 조회
2. 각 파일 삭제

---

#### 7. `extract_s3_keys_from_content(html_content)`

HTML 본문에서 S3 이미지 키를 추출합니다.

**용도:**
- 기존 이미지와 새 이미지를 비교하여 사용되지 않는 이미지 삭제

---

#### 8. `convert_s3_urls_to_presigned(html_content, expires_in=3600)`

HTML 본문의 S3 이미지 URL을 Presigned URL로 변환합니다.

**처리:**
1. `<img>` 태그에서 S3 URL 추출
2. 각 URL을 Presigned URL로 변환
3. base64 이미지는 그대로 유지

**Presigned URL:**
- 만료 시간: 기본 1시간 (3600초)
- Private S3 버킷에 접근하기 위해 필요

---

#### 9. `get_presigned_thumbnail_url(thumbnail_url, expires_in=3600)`

썸네일 URL을 Presigned URL로 변환합니다.

**처리:**
- base64 이미지: 그대로 반환
- S3 URL: Presigned URL로 변환
- 기타 URL: 그대로 반환

---

## 주요 비즈니스 로직

### 1. 아티클 생성 시 이미지 처리

```
1. 아티클 생성 (ID 획득)
2. 본문의 base64 이미지 → S3 업로드 → URL 교체
3. 썸네일 base64 → S3 업로드 → URL 저장
4. 응답 시 Presigned URL로 변환
```

---

### 2. 아티클 수정 시 이미지 처리

```
1. 기존 이미지 키 추출
2. 본문 변경 시:
   - base64 이미지 → S3 업로드 → URL 교체
   - 사용되지 않는 기존 이미지 삭제
3. 썸네일 변경 시:
   - base64 → S3 업로드
   - 기존 썸네일과 키가 다를 때만 기존 썸네일 삭제
4. 응답 시 Presigned URL로 변환
```

**중요:**
- 썸네일은 `request.data`에 `'thumbnail'` 키가 있을 때만 처리
- 새 썸네일과 기존 썸네일의 키가 같으면 삭제하지 않음 (같은 파일이므로)

---

### 3. 소프트 삭제

- `status='deleted'` 설정
- `deletedAt` 현재 시간 설정
- `deletedBy` 삭제자 정보 설정
- 실제 데이터는 유지 (복구 가능)

---

### 4. 영구 삭제

- 관련 이미지를 S3에서 삭제
- 데이터베이스에서 완전히 삭제

---

### 5. Presigned URL 생성

**이유:**
- S3 버킷이 Private이므로 직접 URL로 접근 불가
- Presigned URL을 통해 임시 접근 권한 부여 (기본 1시간)

**사용 위치:**
- 목록 조회 시 썸네일
- 상세 조회 시 본문 이미지 및 썸네일
- 엑셀 다운로드 시 썸네일

---

## 에러 처리

### 에러 응답 형식

```json
{
  "IndeAPIResponse": {
    "Success": false,
    "ErrorCode": "01",
    "Message": "에러 메시지"
  }
}
```

### 주요 에러 코드

- `"01"`: 입력값 검증 오류
- `"99"`: 서버 내부 오류

### 에러 처리 위치

1. **시리얼라이저 검증 오류**: `serializer.is_valid()` 실패 시
2. **모델 조회 오류**: `Article.DoesNotExist` 예외 처리
3. **S3 업로드 오류**: `utils.py`의 함수에서 예외 처리 및 로깅

---

## 로깅

### 로깅 설정

`config/settings/base.py`에서 로깅 설정:

```python
LOGGING = {
    'loggers': {
        'sites.admin_api.articles': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
        'core.s3_storage': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
    },
}
```

### 로그 파일

- 경로: `logs/django.log`
- 최대 크기: 5MB
- 백업 파일: 5개

### 주요 로깅 포인트

1. **이미지 업로드:**
   - 업로드 시작/성공/실패
   - 파일 크기, S3 키, URL

2. **썸네일 처리:**
   - 썸네일 데이터 수신
   - 업로드 시작/성공/실패
   - 기존 썸네일 삭제

3. **S3 Storage:**
   - 버킷 선택 (개발/프로덕션)
   - 업로드 시도/성공/실패
   - Presigned URL 생성

---

## 환경 변수

### S3 관련 환경 변수

**개발 환경 (`env/.env.local`):**
```env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_REGION_NAME=ap-northeast-2
AWS_STORAGE_BUCKET_NAME_DEVELOPMENT=inde-develope
DJANGO_DEBUG=1
```

**프로덕션 환경 (`env/.env.production`):**
```env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_REGION_NAME=ap-northeast-2
AWS_STORAGE_BUCKET_NAME_PRODUCTION=inde-production
DJANGO_DEBUG=0
```

**메인 환경 변수 파일 (`env/.env`):**
```env
ENV_MODE=local  # 또는 production
```

### 버킷 선택 로직

1. `AWS_STORAGE_BUCKET_NAME`이 명시적으로 설정되어 있으면 사용
2. 그렇지 않으면:
   - `DJANGO_DEBUG=1`이고 `settings.DEBUG=True` → 개발 버킷 (`inde-develope`)
   - 그 외 → 프로덕션 버킷 (`inde-production`)

---

## 주요 개선 사항 및 이슈 해결

### 1. 썸네일 업데이트 로직 개선

**문제:**
- 새로 업로드한 썸네일과 기존 썸네일이 같은 키를 사용할 때, 기존 썸네일 삭제 시 새로 업로드한 파일도 삭제됨

**해결:**
- 새 썸네일과 기존 썸네일의 키를 비교하여 다를 때만 기존 썸네일 삭제

---

### 2. Presigned URL 생성

**문제:**
- Private S3 버킷에 직접 접근 불가

**해결:**
- 모든 S3 이미지 URL을 Presigned URL로 변환하여 응답

---

### 3. content 필드 용량 확장

**문제:**
- 본문에 base64 이미지가 포함될 경우 `TEXT` 타입(약 64KB)으로는 부족

**해결:**
- `MEDIUMTEXT` 타입(약 16MB)으로 변경

---

### 4. 썸네일 base64 처리

**문제:**
- base64 데이터가 500자를 초과하여 `CharField(max_length=500)` 검증 실패

**해결:**
- base64 데이터인 경우 길이 검증 건너뛰기 (S3 업로드 예정이므로)
- URL인 경우만 500자 제한 검증

---

### 5. 썸네일 업데이트 조건

**문제:**
- 썸네일이 변경되지 않았는데도 업데이트 시도

**해결:**
- `request.data`에 `'thumbnail'` 키가 명시적으로 있을 때만 처리
- 프론트엔드에서 썸네일이 변경된 경우에만 전송

---

## 참고 자료

- [Django REST Framework 공식 문서](https://www.django-rest-framework.org/)
- [AWS S3 boto3 문서](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Presigned URL 생성 가이드](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)

---

## 작성일

2026-02-11

## 최종 수정일

2026-02-11

