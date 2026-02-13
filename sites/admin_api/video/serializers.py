"""
비디오/세미나 시리얼라이저
"""
from rest_framework import serializers
from sites.admin_api.video.models import Video


class VideoSerializer(serializers.ModelSerializer):
    """비디오 시리얼라이저 (전체 필드)"""
    
    displayId = serializers.SerializerMethodField()
    
    class Meta:
        model = Video
        fields = [
            'id',
            'displayId',
            'contentType',
            'category',
            'title',
            'subtitle',
            'body',
            'videoStreamId',
            'videoUrl',
            'thumbnail',
            'speaker',
            'speakerAffiliation',
            'editor',
            'director',
            'visibility',
            'status',
            'isNewBadge',
            'isMaterialBadge',
            'allowRating',
            'allowComment',
            'viewCount',
            'rating',
            'commentCount',
            'tags',
            'questions',
            'attachments',
            'scheduledAt',
            'deletedAt',
            'deletedBy',
            'createdAt',
            'updatedAt',
        ]
        read_only_fields = [
            'id',
            'displayId',
            'viewCount',
            'commentCount',
            'createdAt',
            'updatedAt',
        ]
    
    def get_displayId(self, obj):
        """표시용 ID 반환"""
        return obj.get_display_id()
    
    def validate_title(self, value):
        """제목 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('제목은 필수입니다.')
        return value.strip()
    
    def validate_contentType(self, value):
        """콘텐츠 타입 검증"""
        if value not in ['video', 'seminar']:
            raise serializers.ValidationError('콘텐츠 타입은 video 또는 seminar여야 합니다.')
        return value
    
    def validate_category(self, value):
        """카테고리 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('카테고리는 필수입니다.')
        return value.strip()
    
    def validate_videoUrl(self, value):
        """영상 URL 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('영상 URL은 필수입니다.')
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


class VideoListSerializer(serializers.ModelSerializer):
    """비디오 목록 시리얼라이저 (간소화된 필드)"""
    
    displayId = serializers.SerializerMethodField()
    
    class Meta:
        model = Video
        fields = [
            'id',
            'displayId',
            'contentType',
            'category',
            'title',
            'subtitle',
            'videoStreamId',
            'thumbnail',
            'speaker',
            'speakerAffiliation',
            'editor',
            'director',
            'visibility',
            'status',
            'isNewBadge',
            'isMaterialBadge',
            'viewCount',
            'rating',
            'commentCount',
            'scheduledAt',
            'deletedAt',
            'deletedBy',
            'createdAt',
            'updatedAt',
        ]
        read_only_fields = [
            'id',
            'displayId',
            'viewCount',
            'commentCount',
            'createdAt',
            'updatedAt',
        ]
    
    def get_displayId(self, obj):
        """표시용 ID 반환"""
        return obj.get_display_id()


class VideoCreateSerializer(serializers.ModelSerializer):
    """비디오 생성 시리얼라이저"""
    
    class Meta:
        model = Video
        fields = [
            'contentType',
            'category',
            'title',
            'subtitle',
            'body',
            'videoStreamId',
            'videoUrl',
            'thumbnail',
            'speaker',
            'speakerAffiliation',
            'editor',
            'director',
            'visibility',
            'status',
            'isNewBadge',
            'isMaterialBadge',
            'allowRating',
            'allowComment',
            'tags',
            'questions',
            'attachments',
            'scheduledAt',
        ]
    
    def validate_title(self, value):
        """제목 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('제목은 필수입니다.')
        return value.strip()
    
    def validate_contentType(self, value):
        """콘텐츠 타입 검증"""
        if value not in ['video', 'seminar']:
            raise serializers.ValidationError('콘텐츠 타입은 video 또는 seminar여야 합니다.')
        return value
    
    def validate_category(self, value):
        """카테고리 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('카테고리는 필수입니다.')
        return value.strip()
    
    def validate_videoUrl(self, value):
        """영상 URL 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('영상 URL은 필수입니다.')
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


class VideoUpdateSerializer(serializers.ModelSerializer):
    """비디오 수정 시리얼라이저"""
    
    class Meta:
        model = Video
        fields = [
            'contentType',
            'category',
            'title',
            'subtitle',
            'body',
            'videoStreamId',
            'videoUrl',
            'thumbnail',
            'speaker',
            'speakerAffiliation',
            'editor',
            'director',
            'visibility',
            'status',
            'isNewBadge',
            'isMaterialBadge',
            'allowRating',
            'allowComment',
            'tags',
            'questions',
            'attachments',
            'scheduledAt',
        ]
        # partial 업데이트 허용 (일부 필드만 업데이트 가능)
        extra_kwargs = {
            'title': {'required': False},
            'contentType': {'required': False},
            'category': {'required': False},
            'videoUrl': {'required': False},
        }
    
    def validate_title(self, value):
        """제목 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('제목은 필수입니다.')
        return value.strip() if value else value
    
    def validate_contentType(self, value):
        """콘텐츠 타입 검증"""
        if value is not None and value not in ['video', 'seminar']:
            raise serializers.ValidationError('콘텐츠 타입은 video 또는 seminar여야 합니다.')
        return value
    
    def validate_category(self, value):
        """카테고리 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('카테고리는 필수입니다.')
        return value.strip() if value else value
    
    def validate_videoUrl(self, value):
        """영상 URL 검증 (레거시 지원)"""
        if value:
            return value.strip()
        return value
    
    def validate_visibility(self, value):
        """공개 범위 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('공개 범위는 필수입니다.')
        return value.strip() if value else value
    
    def validate_status(self, value):
        """상태 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('상태는 필수입니다.')
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

