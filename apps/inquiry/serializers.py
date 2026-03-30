import os

from rest_framework import serializers

from .models import Inquiry

_MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
_ALLOWED_ATTACHMENT_EXT = {".jpg", ".jpeg", ".png", ".pdf", ".zip"}


def _validate_attachment_file(value):
    if not value:
        return value
    if value.size > _MAX_ATTACHMENT_BYTES:
        raise serializers.ValidationError("첨부 파일은 10MB 이하여야 합니다.")
    name = getattr(value, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    if ext not in _ALLOWED_ATTACHMENT_EXT:
        raise serializers.ValidationError("jpg, png, pdf, zip 형식만 지원합니다.")
    return value


class InquiryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = ("id", "title", "inquiry_type", "status", "created_at")


class InquiryDetailSerializer(serializers.ModelSerializer):
    attachment = serializers.SerializerMethodField()

    class Meta:
        model = Inquiry
        fields = (
            "id",
            "title",
            "inquiry_type",
            "content",
            "attachment",
            "answer",
            "status",
            "created_at",
        )

    def get_attachment(self, obj: Inquiry):
        if not obj.attachment:
            return None
        request = self.context.get("request")
        url = obj.attachment.url
        if request:
            return request.build_absolute_uri(url)
        return url


class InquiryCreateSerializer(serializers.ModelSerializer):
    inquiry_type = serializers.CharField(max_length=64)
    attachment = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Inquiry
        fields = ("title", "content", "inquiry_type", "attachment")

    def validate_attachment(self, value):
        return _validate_attachment_file(value)


class InquiryAnswerSerializer(serializers.ModelSerializer):
    """관리자 답변용: answer만 수정 가능, status는 서버에서 자동 변경"""

    class Meta:
        model = Inquiry
        fields = ("answer",)
