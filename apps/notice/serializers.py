from rest_framework import serializers

from sites.admin_api.articles.utils import normalize_empty_p_tags

from .models import Notice


class NoticeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ("id", "title", "is_pinned", "show_in_gnb", "view_count", "created_at")


class NoticeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ("id", "title", "content", "is_pinned", "show_in_gnb", "view_count", "created_at")


class NoticeCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ("title", "content", "is_pinned", "show_in_gnb")

    def validate_content(self, value):
        """TipTap 빈 단락 `<p></p>` 등 → `<br />` (contentEditor.md §2.1, 아티클과 동일)."""
        if value:
            return normalize_empty_p_tags(value)
        return value
