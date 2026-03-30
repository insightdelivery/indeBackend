"""
관리자용 게시판 시리얼라이저 (문의 목록/상세에 회원 정보 포함)
"""
from rest_framework import serializers
from apps.inquiry.serializers import InquiryListSerializer, InquiryDetailSerializer
from apps.inquiry.models import Inquiry


class AdminInquiryListSerializer(InquiryListSerializer):
    """목록: 회원 member_sid, name 포함 + 답변 메일 발송/열람"""
    member = serializers.SerializerMethodField()

    class Meta(InquiryListSerializer.Meta):
        fields = InquiryListSerializer.Meta.fields + (
            "member",
            "answer_email_sent_at",
            "answer_email_opened_at",
        )

    def get_member(self, obj: Inquiry):
        u = getattr(obj, "user", None)
        if not u:
            return None
        return {
            "member_sid": u.member_sid,
            "name": u.name or "",
        }


class AdminInquiryDetailSerializer(InquiryDetailSerializer):
    """상세: 회원 member_sid, name, email, phone 포함 + 답변 메일 발송/열람"""
    member = serializers.SerializerMethodField()

    class Meta(InquiryDetailSerializer.Meta):
        fields = InquiryDetailSerializer.Meta.fields + (
            "member",
            "answer_email_sent_at",
            "answer_email_opened_at",
        )

    def get_member(self, obj: Inquiry):
        u = getattr(obj, "user", None)
        if not u:
            return None
        return {
            "member_sid": u.member_sid,
            "name": u.name or "",
            "email": u.email or "",
            "phone": getattr(u, "phone", None) or "",
        }


class AdminInquiryAnswerSerializer(serializers.ModelSerializer):
    """답변 저장 + 선택적 안내 메일 발송"""

    send_email = serializers.BooleanField(required=False, default=True, write_only=True)

    class Meta:
        model = Inquiry
        fields = ("answer", "send_email")

    def update(self, instance, validated_data):
        self._send_email_flag = validated_data.pop("send_email", True)
        return super().update(instance, validated_data)

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        if getattr(self, "_send_email_flag", False):
            from apps.inquiry.email_notify import send_inquiry_answer_notification

            send_inquiry_answer_notification(instance)
        return instance
