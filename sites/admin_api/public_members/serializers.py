"""
관리자용 PublicMemberShip 시리얼라이저 (비밀번호 제외 노출, 수정 시에만 반영)
"""
from rest_framework import serializers
from sites.public_api.models import PublicMemberShip


class PublicMemberListSerializer(serializers.ModelSerializer):
    """목록용: 비밀번호 제외, 탈퇴 상태 포함"""
    class Meta:
        model = PublicMemberShip
        fields = (
            "member_sid", "email", "name", "nickname", "phone",
            "position", "joined_via", "is_staff", "is_active",
            "email_verified", "profile_completed", "newsletter_agree",
            "last_login", "created_at", "updated_at",
            "status",
            "withdraw_requested_at", "withdraw_completed_at",
        )


class PublicMemberDetailSerializer(serializers.ModelSerializer):
    """상세용: 비밀번호 제외, 모든 필드, 탈퇴 정보 포함"""
    class Meta:
        model = PublicMemberShip
        fields = (
            "member_sid", "email", "name", "nickname", "phone",
            "position", "birth_year", "birth_month", "birth_day",
            "region_type", "region_domestic", "region_foreign",
            "joined_via", "sns_provider_uid",
            "newsletter_agree", "profile_completed", "email_verified",
            "is_staff", "is_active",
            "last_login", "created_at", "updated_at",
            "status",
            "withdraw_reason", "withdraw_detail_reason",
            "withdraw_requested_at", "withdraw_completed_at",
            "withdraw_ip", "withdraw_user_agent",
        )


class PublicMemberCreateUpdateSerializer(serializers.ModelSerializer):
    """생성/수정: password는 write_only, 저장 시 set_password 사용. 관리자용 status/탈퇴 필드 수정 가능."""
    password = serializers.CharField(required=False, write_only=True, allow_blank=True, min_length=8)
    status = serializers.ChoiceField(choices=PublicMemberShip.STATUS_CHOICES, required=False)
    withdraw_reason = serializers.CharField(required=False, allow_blank=True)
    withdraw_detail_reason = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = PublicMemberShip
        fields = (
            "email", "name", "nickname", "phone", "password",
            "position", "birth_year", "birth_month", "birth_day",
            "region_type", "region_domestic", "region_foreign",
            "joined_via", "newsletter_agree", "profile_completed",
            "email_verified", "is_staff", "is_active",
            "status", "withdraw_reason", "withdraw_detail_reason",
        )

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        validated_data.pop("status", None)
        validated_data.pop("withdraw_reason", None)
        validated_data.pop("withdraw_detail_reason", None)
        member = PublicMemberShip.objects.create(**validated_data)
        if password:
            member.set_password(password)
            member.save(update_fields=["password"])
        return member

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        new_status = validated_data.get("status")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        if new_status == PublicMemberShip.STATUS_WITHDRAWN:
            instance.is_active = False
        elif new_status in (PublicMemberShip.STATUS_ACTIVE, PublicMemberShip.STATUS_WITHDRAW_REQUEST):
            instance.is_active = True
        instance.save()
        return instance
