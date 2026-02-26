from rest_framework import serializers
from .models import Inquiry


class InquiryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = ("id", "title", "status", "created_at")


class InquiryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = ("id", "title", "content", "answer", "status", "created_at")


class InquiryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = ("title", "content")


class InquiryAnswerSerializer(serializers.ModelSerializer):
    """관리자 답변용: answer만 수정 가능, status는 서버에서 자동 변경"""
    class Meta:
        model = Inquiry
        fields = ("answer",)
