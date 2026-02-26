from rest_framework import serializers
from .models import Notice


class NoticeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ("id", "title", "is_pinned", "view_count", "created_at")


class NoticeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ("id", "title", "content", "is_pinned", "view_count", "created_at")


class NoticeCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ("title", "content", "is_pinned")
