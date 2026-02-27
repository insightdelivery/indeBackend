"""
관리자용 PublicMemberShip 시리얼라이저 (비밀번호 제외 노출, 수정 시에만 반영)
"""
from rest_framework import serializers
from sites.public_api.models import PublicMemberShip


class PublicMemberListSerializer(serializers.ModelSerializer):
    """목록용: 비밀번호 제외"""
    class Meta:
        model = PublicMemberShip
        fields = (
            "member_sid", "email", "name", "nickname", "phone",
            "position", "joined_via", "is_staff", "is_active",
            "email_verified", "profile_completed", "newsletter_agree",
            "last_login", "created_at", "updated_at",
        )


class PublicMemberDetailSerializer(serializers.ModelSerializer):
    """상세용: 비밀번호 제외, 모든 필드"""
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
        )


class PublicMemberCreateUpdateSerializer(serializers.ModelSerializer):
    """생성/수정: password는 write_only, 저장 시 set_password 사용"""
    password = serializers.CharField(required=False, write_only=True, allow_blank=True, min_length=8)

    class Meta:
        model = PublicMemberShip
        fields = (
            "email", "name", "nickname", "phone", "password",
            "position", "birth_year", "birth_month", "birth_day",
            "region_type", "region_domestic", "region_foreign",
            "joined_via", "newsletter_agree", "profile_completed",
            "email_verified", "is_staff", "is_active",
        )

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        member = PublicMemberShip.objects.create(**validated_data)
        if password:
            member.set_password(password)
            member.save(update_fields=["password"])
        return member

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
