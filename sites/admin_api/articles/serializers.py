"""
아티클 시리얼라이저
"""
from rest_framework import serializers
from sites.admin_api.articles.models import Article


class ArticleSerializer(serializers.ModelSerializer):
    """아티클 시리얼라이저 (전체 필드)"""

    authorProfileImage = serializers.SerializerMethodField()

    def get_authorProfileImage(self, obj):
        """연결된 ContentAuthor.profile_image (없으면 null). 공개 상세에서 presigned 처리."""
        rel = getattr(obj, 'author_id', None)
        if rel is None:
            return None
        url = getattr(rel, 'profile_image', None) or ''
        url = url.strip()
        return url or None

    class Meta:
        model = Article
        fields = [
            'id',
            'title',
            'subtitle',
            'content',
            'thumbnail',
            'category',
            'author',
            'author_id',
            'authorProfileImage',
            'authorAffiliation',
            'visibility',
            'status',
            'isEditorPick',
            'viewCount',
            'rating',
            'commentCount',
            'highlightCount',
            'questionCount',
            'tags',
            'previewLength',
            'scheduledAt',
            'deletedAt',
            'deletedBy',
            'createdAt',
            'updatedAt',
        ]
        read_only_fields = ['id', 'viewCount', 'commentCount', 'highlightCount', 'questionCount', 'createdAt', 'updatedAt']
    
    def validate_title(self, value):
        """제목 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('제목은 필수입니다.')
        return value.strip()
    
    def validate_content(self, value):
        """본문 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('본문 내용은 필수입니다.')
        return value.strip()
    
    def validate_category(self, value):
        """카테고리 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('카테고리는 필수입니다.')
        return value.strip()
    
    def validate_author(self, value):
        """작성자 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('작성자는 필수입니다.')
        return value.strip()


class ArticleListSerializer(serializers.ModelSerializer):
    """아티클 목록 시리얼라이저 (간소화된 필드)"""

    authorProfileImage = serializers.SerializerMethodField()

    def get_authorProfileImage(self, obj):
        """연결 ContentAuthor.profile_image (없으면 null). 공개 목록에서 presigned 처리는 뷰에서."""
        rel = getattr(obj, 'author_id', None)
        if rel is None:
            return None
        url = getattr(rel, 'profile_image', None) or ''
        url = url.strip()
        return url or None

    class Meta:
        model = Article
        fields = [
            'id',
            'title',
            'subtitle',
            'thumbnail',
            'category',
            'author',
            'author_id',
            'authorProfileImage',
            'authorAffiliation',
            'visibility',
            'status',
            'isEditorPick',
            'viewCount',
            'rating',
            'commentCount',
            'highlightCount',
            'questionCount',
            'tags',
            'previewLength',
            'scheduledAt',
            'deletedAt',
            'deletedBy',
            'createdAt',
            'updatedAt',
        ]
        read_only_fields = ['id', 'viewCount', 'commentCount', 'highlightCount', 'questionCount', 'createdAt', 'updatedAt']


class ArticleCreateSerializer(serializers.ModelSerializer):
    """아티클 생성 시리얼라이저. author_id 선택 시 author는 ContentAuthor.name, authorAffiliation은 role(DIRECTOR/EDITOR)에 따라 뷰에서 자동 설정."""
    # 썸네일: 이미지 업로드(base64)만 허용. 글자 수 검증 없음(모델 max_length 상속 안 함)
    thumbnail = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Article
        fields = [
            'title',
            'subtitle',
            'content',
            'thumbnail',
            'category',
            'author',
            'author_id',
            'authorAffiliation',
            'visibility',
            'status',
            'isEditorPick',
            'tags',
            'previewLength',
            'scheduledAt',
        ]
    
    def validate(self, attrs):
        """author_id 없으면 author(문자열) 필수."""
        author_id = attrs.get('author_id')
        author = attrs.get('author') or (self.initial_data.get('author') if self.initial_data else None)
        if not author_id and (not author or (isinstance(author, str) and not author.strip())):
            raise serializers.ValidationError({'author': '작성자(에디터)를 선택하거나 작성자명을 입력해주세요.'})
        return attrs
    
    def validate_title(self, value):
        """제목 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('제목은 필수입니다.')
        return value.strip()
    
    def validate_content(self, value):
        """본문 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('본문 내용은 필수입니다.')
        return value.strip()
    
    def validate_category(self, value):
        """카테고리 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('카테고리는 필수입니다.')
        return value.strip()
    
    def validate_author(self, value):
        """작성자 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('작성자는 필수입니다.')
        return value.strip()


class ArticleUpdateSerializer(serializers.ModelSerializer):
    """아티클 수정 시리얼라이저. author_id 선택 시 author는 ContentAuthor.name, authorAffiliation은 role에 따라 뷰에서 자동 설정."""
    # 썸네일: 이미지 업로드(base64)만 허용. 글자 수 검증 없음
    thumbnail = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Article
        fields = [
            'title',
            'subtitle',
            'content',
            'thumbnail',
            'category',
            'author',
            'author_id',
            'authorAffiliation',
            'visibility',
            'status',
            'isEditorPick',
            'tags',
            'previewLength',
            'scheduledAt',
        ]
        # partial 업데이트 허용 (일부 필드만 업데이트 가능)
        extra_kwargs = {
            'title': {'required': False},
            'content': {'required': False},
            'category': {'required': False},
            'author': {'required': False},
            'author_id': {'required': False},
        }
    
    def validate_title(self, value):
        """제목 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('제목은 필수입니다.')
        return value.strip() if value else value
    
    def validate_content(self, value):
        """본문 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('본문 내용은 필수입니다.')
        return value.strip() if value else value
    
    def validate_category(self, value):
        """카테고리 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('카테고리는 필수입니다.')
        return value.strip() if value else value
    
    def validate_author(self, value):
        """작성자 검증 (author_id 없을 때만 비어 있으면 안 됨, validate()에서 처리)"""
        if value is not None and value.strip() == '':
            return value
        return value.strip() if value else value
    
    def validate_visibility(self, value):
        """공개 범위 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('공개 범위는 필수입니다.')
        return value.strip() if value else value
    
    def validate_status(self, value):
        """발행 상태 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('발행 상태는 필수입니다.')
        return value.strip() if value else value

