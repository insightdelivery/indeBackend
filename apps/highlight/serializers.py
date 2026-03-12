"""
Article Highlight Serializer (articleHightlightPlan.md §4)
- color: 색상 식별자(yellow/green/blue/pink) 또는 헥스값(#RRGGBB 등) 허용
"""
import re
from rest_framework import serializers
from .models import ArticleHighlight

# 기존 식별자 또는 #으로 시작하는 hex (#RRGGBB, #RRGGBBAA)
COLOR_PATTERN = re.compile(r'^(yellow|green|blue|pink)$|^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$')


def validate_color(value):
    if not value or len(value) > 20:
        raise serializers.ValidationError('color는 1~20자이며, 식별자(yellow/green/blue/pink) 또는 hex(#RRGGBB) 형식이어야 합니다.')
    if not COLOR_PATTERN.match(value.strip()):
        raise serializers.ValidationError('color는 yellow/green/blue/pink 또는 #RRGGBB 형식이어야 합니다.')
    return value.strip()


class ArticleHighlightSerializer(serializers.ModelSerializer):
    highlightId = serializers.IntegerField(source='id', read_only=True)
    articleId = serializers.IntegerField(source='article_id', read_only=True)
    highlightGroupId = serializers.IntegerField(source='highlight_group_id', read_only=True)
    paragraphIndex = serializers.IntegerField(source='paragraph_index')
    highlightText = serializers.CharField(source='highlight_text')
    prefixText = serializers.CharField(source='prefix_text', required=False, allow_blank=True, default='')
    suffixText = serializers.CharField(source='suffix_text', required=False, allow_blank=True, default='')
    startOffset = serializers.IntegerField(source='start_offset')
    endOffset = serializers.IntegerField(source='end_offset')
    color = serializers.CharField(max_length=20, default='yellow')
    createdAt = serializers.DateTimeField(source='created_at', read_only=True, format='%Y-%m-%dT%H:%M:%S')

    class Meta:
        model = ArticleHighlight
        fields = [
            'highlightId', 'articleId', 'highlightGroupId', 'paragraphIndex',
            'highlightText', 'prefixText', 'suffixText', 'startOffset', 'endOffset',
            'color', 'createdAt',
        ]
        read_only_fields = ['highlightId', 'articleId', 'highlightGroupId', 'createdAt']


class ArticleHighlightCreateSerializer(serializers.Serializer):
    """생성 요청 단일 또는 배열 요소"""
    articleId = serializers.IntegerField()
    highlightGroupId = serializers.IntegerField(required=False, allow_null=True)
    paragraphIndex = serializers.IntegerField()
    highlightText = serializers.CharField()
    prefixText = serializers.CharField(required=False, allow_blank=True, default='')
    suffixText = serializers.CharField(required=False, allow_blank=True, default='')
    startOffset = serializers.IntegerField()
    endOffset = serializers.IntegerField()
    color = serializers.CharField(max_length=20, default='yellow')

    def validate_color(self, value):
        return validate_color(value or 'yellow')
