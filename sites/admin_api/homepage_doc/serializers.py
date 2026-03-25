from rest_framework import serializers

from .models import HomepageDocInfo


class HomepageDocReadSerializer(serializers.ModelSerializer):
    """camelCase 응답 (§4.7) — body_html은 LONGTEXT"""

    docType = serializers.CharField(source='doc_type', read_only=True)
    bodyHtml = serializers.CharField(source='body_html', read_only=True)
    isPublished = serializers.BooleanField(source='is_published', read_only=True)

    class Meta:
        model = HomepageDocInfo
        fields = ('docType', 'title', 'bodyHtml', 'isPublished')


class HomepageDocPutSerializer(serializers.Serializer):
    title = serializers.CharField(allow_null=True, required=False)
    bodyHtml = serializers.CharField(required=False, allow_blank=True)
    isPublished = serializers.BooleanField(required=False)

    def validate(self, attrs):
        # PUT 시 문서에서 권장하는 필드 세트 — 없으면 기본값 처리는 뷰에서
        return attrs
