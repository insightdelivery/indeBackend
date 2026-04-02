from rest_framework import serializers

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email

from .models import MessageBatch, MessageDetail, KakaoTemplate, MessageSenderNumber, MessageSenderEmail, MessageTemplate


def normalize_phone(value: str) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value if ch.isdigit())


class KakaoTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KakaoTemplate
        fields = [
            "id",
            "template_code",
            "template_name",
            "content",
            "variables",
            "buttons",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MessageDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageDetail
        fields = [
            "id",
            "receiver_name",
            "receiver_phone",
            "receiver_email",
            "template_id",
            "template_name",
            "variables",
            "final_content",
            "status",
            "external_code",
            "external_message",
            "error_reason",
            "sent_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MessageBatchListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageBatch
        fields = [
            "id",
            "type",
            "sender",
            "title",
            "content",
            "total_count",
            "success_count",
            "fail_count",
            "excluded_count",
            "status",
            "requested_at",
            "scheduled_at",
            "completed_at",
            "created_at",
        ]


class MessageBatchSerializer(serializers.ModelSerializer):
    details = MessageDetailSerializer(many=True, read_only=True)

    class Meta:
        model = MessageBatch
        fields = [
            "id",
            "type",
            "sender",
            "title",
            "content",
            "total_count",
            "success_count",
            "fail_count",
            "excluded_count",
            "status",
            "requested_at",
            "scheduled_at",
            "started_at",
            "completed_at",
            "canceled_at",
            "is_processed",
            "request_snapshot",
            "result_snapshot",
            "api_response_logs",
            "created_by_id",
            "created_at",
            "updated_at",
            "details",
        ]
        read_only_fields = ["id", "requested_at", "created_at", "updated_at", "details"]


class MessageDetailCreateSerializer(serializers.Serializer):
    receiver_name = serializers.CharField(required=False, allow_blank=True, default="")
    receiver_phone = serializers.CharField(required=False, allow_blank=True, default="")
    receiver_email = serializers.CharField(required=False, allow_blank=True, default="")
    template_id = serializers.IntegerField(required=False, allow_null=True)
    template_name = serializers.CharField(required=False, allow_blank=True, default="")
    variables = serializers.JSONField(required=False, default=dict)
    final_content = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(choices=MessageDetail.STATUS_CHOICES, required=False, default=MessageDetail.STATUS_EXCLUDED)

    def validate_receiver_phone(self, value: str) -> str:
        v = normalize_phone(value)
        if v and not v.startswith("01"):
            raise serializers.ValidationError("휴대전화번호 형식이 올바르지 않습니다.")
        return v


class MessageBatchCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=MessageBatch.TYPE_CHOICES)
    sender = serializers.CharField(max_length=120)
    title = serializers.CharField(required=False, allow_blank=True, default="")
    content = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(choices=MessageBatch.STATUS_CHOICES, required=False, default=MessageBatch.STATUS_PROCESSING)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    request_snapshot = serializers.JSONField(required=False, default=dict)
    details = MessageDetailCreateSerializer(many=True)

    def validate(self, attrs):
        details = attrs.get("details") or []
        if not details:
            raise serializers.ValidationError("최소 1명 이상의 수신자가 필요합니다.")
        return attrs


class MessageSenderNumberSerializer(serializers.ModelSerializer):
    # soft delete 재등록(복구) 처리를 위해 기본 unique validator를 비활성화
    sender_number = serializers.CharField(validators=[])

    class Meta:
        model = MessageSenderNumber
        fields = [
            "id",
            "sender_number",
            "manager_name",
            "comment",
            "request_type",
            "status",
            "reject_reason",
            "requested_at",
            "processed_at",
            "created_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "requested_at", "processed_at", "created_at", "updated_at", "created_by_id"]

    def validate_sender_number(self, value: str) -> str:
        normalized = "".join(ch for ch in value if ch.isdigit())
        if not normalized:
            raise serializers.ValidationError("발신번호를 입력해 주세요.")
        if len(normalized) < 8 or len(normalized) > 12:
            raise serializers.ValidationError("발신번호 형식이 올바르지 않습니다.")
        return normalized


class MessageSenderEmailSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(validators=[])

    class Meta:
        model = MessageSenderEmail
        fields = [
            "id",
            "sender_email",
            "manager_name",
            "comment",
            "request_type",
            "status",
            "reject_reason",
            "requested_at",
            "processed_at",
            "created_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "requested_at", "processed_at", "created_at", "updated_at", "created_by_id"]

    def validate_sender_email(self, value: str) -> str:
        v = (value or "").strip().lower()
        if not v:
            raise serializers.ValidationError("발신 이메일을 입력해 주세요.")
        try:
            validate_email(v)
        except DjangoValidationError:
            raise serializers.ValidationError("올바른 이메일 형식이 아닙니다.") from None
        return v


class MessageTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTemplate
        fields = [
            "id",
            "channel",
            "template_name",
            "content",
            "is_active",
            "created_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by_id", "created_at", "updated_at"]
