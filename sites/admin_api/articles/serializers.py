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
            'questions',
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
    """아티클 생성 시리얼라이저"""
    
    class Meta:
        model = Article
        fields = [
            'title',
            'subtitle',
            'content',
            'thumbnail',
            'category',
            'author',
            'authorAffiliation',
            'visibility',
            'status',
            'isEditorPick',
            'tags',
            'questions',
            'previewLength',
            'scheduledAt',
        ]
    
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
    """아티클 수정 시리얼라이저"""
    
    class Meta:
        model = Article
        fields = [
            'title',
            'subtitle',
            'content',
            'thumbnail',
            'category',
            'author',
            'authorAffiliation',
            'visibility',
            'status',
            'isEditorPick',
            'tags',
            'questions',
            'previewLength',
            'scheduledAt',
        ]
        # partial 업데이트 허용 (일부 필드만 업데이트 가능)
        extra_kwargs = {
            'title': {'required': False},
            'content': {'required': False},
            'category': {'required': False},
            'author': {'required': False},
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
        """작성자 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('작성자는 필수입니다.')
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

