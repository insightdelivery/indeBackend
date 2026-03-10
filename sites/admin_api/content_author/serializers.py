"""
콘텐츠 저자 시리얼라이저
"""
from rest_framework import serializers
from .models import ContentAuthor, ContentAuthorContentType


class ContentAuthorContentTypeSerializer(serializers.ModelSerializer):
    """저자–콘텐츠 유형 매핑 (중첩용)"""
    content_type_display = serializers.CharField(source='get_content_type_display', read_only=True)

    class Meta:
        model = ContentAuthorContentType
        fields = ['id', 'content_type', 'content_type_display']


class ContentAuthorListSerializer(serializers.ModelSerializer):
    """저자 목록용 (간소화)"""
    content_types = serializers.SerializerMethodField()

    class Meta:
        model = ContentAuthor
        fields = [
            'author_id', 'name', 'profile_image', 'role', 'status',
            'member_ship_sid', 'created_at', 'updated_at', 'content_types',
        ]

    def get_content_types(self, obj):
        return [ct.content_type for ct in obj.content_types.all()]


class ContentAuthorDetailSerializer(serializers.ModelSerializer):
    """저자 상세 (담당 콘텐츠 유형 목록 포함)"""
    content_types = ContentAuthorContentTypeSerializer(many=True, read_only=True)

    class Meta:
        model = ContentAuthor
        fields = [
            'author_id', 'name', 'profile_image', 'role', 'status',
            'member_ship_sid', 'created_at', 'updated_at', 'content_types',
        ]


class ContentAuthorCreateSerializer(serializers.Serializer):
    """저자 등록"""
    name = serializers.CharField(max_length=100)
    profile_image = serializers.CharField(max_length=500, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=ContentAuthor.ROLE_CHOICES, default=ContentAuthor.ROLE_EDITOR)
    status = serializers.ChoiceField(choices=ContentAuthor.STATUS_CHOICES, default=ContentAuthor.STATUS_ACTIVE)
    member_ship_sid = serializers.CharField(max_length=15, required=False, allow_blank=True, allow_null=True)
    content_types = serializers.ListField(
        child=serializers.ChoiceField(choices=ContentAuthorContentType.CONTENT_TYPE_CHOICES),
        required=False,
        allow_empty=True,
    )

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('이름은 필수입니다.')
        return value.strip()


class ContentAuthorUpdateSerializer(serializers.Serializer):
    """저자 수정"""
    name = serializers.CharField(max_length=100, required=False)
    profile_image = serializers.CharField(max_length=500, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=ContentAuthor.ROLE_CHOICES, required=False)
    status = serializers.ChoiceField(choices=ContentAuthor.STATUS_CHOICES, required=False)
    member_ship_sid = serializers.CharField(max_length=15, required=False, allow_blank=True, allow_null=True)
    content_types = serializers.ListField(
        child=serializers.ChoiceField(choices=ContentAuthorContentType.CONTENT_TYPE_CHOICES),
        required=False,
        allow_empty=True,
    )

    def validate_name(self, value):
        if value is not None and (not value or not value.strip()):
            raise serializers.ValidationError('이름은 비워둘 수 없습니다.')
        return value.strip() if value else value
