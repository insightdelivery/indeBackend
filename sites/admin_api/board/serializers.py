"""
관리자용 게시판 시리얼라이저 (문의 목록/상세에 회원 정보 포함)
"""
from rest_framework import serializers
from apps.inquiry.serializers import InquiryListSerializer, InquiryDetailSerializer
from apps.inquiry.models import Inquiry


class AdminInquiryListSerializer(InquiryListSerializer):
    """목록: 회원 member_sid, name 포함"""
    member = serializers.SerializerMethodField()

    class Meta(InquiryListSerializer.Meta):
        fields = InquiryListSerializer.Meta.fields + ("member",)

    def get_member(self, obj: Inquiry):
        u = getattr(obj, "user", None)
        if not u:
            return None
        return {
            "member_sid": u.member_sid,
            "name": u.name or "",
        }


class AdminInquiryDetailSerializer(InquiryDetailSerializer):
    """상세: 회원 member_sid, name, email, phone 포함"""
    member = serializers.SerializerMethodField()

    class Meta(InquiryDetailSerializer.Meta):
        fields = InquiryDetailSerializer.Meta.fields + ("member",)

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
