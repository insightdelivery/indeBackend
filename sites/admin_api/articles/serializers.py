"""
아티클 시리얼라이저
"""
from rest_framework import serializers
from sites.admin_api.articles.models import Article


class ArticleSerializer(serializers.ModelSerializer):
    """아티클 시리얼라이저 (전체 필드)"""
    
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
    """아티클 생성 시리얼라이저. author_id 선택 시 author는 ContentAuthor.name으로 자동 설정됨."""
    
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
    
    def validate_thumbnail(self, value):
        """썸네일 검증 - base64 데이터는 검증 건너뛰기"""
        if not value:
            return value
        
        # base64 데이터인 경우 (S3에 업로드될 예정이므로 검증 건너뛰기)
        if value.startswith('data:image'):
            return value
        
        # URL인 경우만 길이 검증
        if len(value) > 500:
            raise serializers.ValidationError('썸네일 URL은 500자를 초과할 수 없습니다.')
        
        return value


class ArticleUpdateSerializer(serializers.ModelSerializer):
    """아티클 수정 시리얼라이저. author_id 선택 시 author는 ContentAuthor.name으로 자동 설정됨."""
    
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
    
    def validate_thumbnail(self, value):
        """썸네일 검증 - base64 데이터는 검증 건너뛰기"""
        if not value:
            return value
        
        # base64 데이터인 경우 (S3에 업로드될 예정이므로 검증 건너뛰기)
        if value.startswith('data:image'):
            return value
        
        # URL인 경우만 길이 검증
        if len(value) > 500:
            raise serializers.ValidationError('썸네일 URL은 500자를 초과할 수 없습니다.')
        
        return value

