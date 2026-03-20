from rest_framework import serializers

from .link_url import normalize_link_url
from .models import DisplayEvent
from .sys_code import validate_content_type_code, validate_event_type_code


class DisplayEventWriteSerializer(serializers.ModelSerializer):
    """관리자용 — camelCase 입력 허용 (프론트 TS와 정합)."""

    eventTypeCode = serializers.CharField(source="event_type_code", max_length=15)
    contentTypeCode = serializers.CharField(source="content_type_code", max_length=15)
    contentId = serializers.IntegerField(source="content_id", required=False, allow_null=True)
    imageUrl = serializers.CharField(source="image_url", required=False, allow_null=True, allow_blank=True)
    linkUrl = serializers.CharField(source="link_url", required=False, allow_null=True, allow_blank=True)
    displayOrder = serializers.IntegerField(source="display_order", required=False, default=0)
    isActive = serializers.BooleanField(source="is_active", required=False, default=True)
    startAt = serializers.DateTimeField(source="start_at", required=False, allow_null=True)
    endAt = serializers.DateTimeField(source="end_at", required=False, allow_null=True)

    class Meta:
        model = DisplayEvent
        fields = (
            "eventTypeCode",
            "contentTypeCode",
            "contentId",
            "title",
            "subtitle",
            "imageUrl",
            "linkUrl",
            "displayOrder",
            "isActive",
            "startAt",
            "endAt",
        )

    def validate(self, attrs):
        inst = self.instance

        event_type = attrs.get("event_type_code", getattr(inst, "event_type_code", None) if inst else None)
        content_type = attrs.get("content_type_code", getattr(inst, "content_type_code", None) if inst else None)

        if not event_type:
            raise serializers.ValidationError({"eventTypeCode": "필수입니다."})
        if not content_type:
            raise serializers.ValidationError({"contentTypeCode": "필수입니다."})

        if inst is None:
            if not validate_event_type_code(event_type):
                raise serializers.ValidationError({"eventTypeCode": "유효하지 않은 코드입니다."})
            if not validate_content_type_code(content_type):
                raise serializers.ValidationError({"contentTypeCode": "유효하지 않은 코드입니다."})
        else:
            if "event_type_code" in attrs and not validate_event_type_code(event_type):
                raise serializers.ValidationError({"eventTypeCode": "유효하지 않은 코드입니다."})
            if "content_type_code" in attrs and not validate_content_type_code(content_type):
                raise serializers.ValidationError({"contentTypeCode": "유효하지 않은 코드입니다."})

        if "content_id" in attrs:
            content_id = attrs["content_id"]
        else:
            content_id = getattr(inst, "content_id", None) if inst else None

        if "link_url" in attrs:
            link_norm = normalize_link_url(attrs["link_url"])
        else:
            link_norm = normalize_link_url(getattr(inst, "link_url", None) if inst else None)

        if content_id is not None:
            if link_norm is not None:
                raise serializers.ValidationError({"linkUrl": "contentId가 있으면 linkUrl을 사용할 수 없습니다."})
            attrs["link_url"] = None
            attrs["content_id"] = int(content_id)
        else:
            attrs["link_url"] = link_norm
            attrs["content_id"] = None

        return attrs
