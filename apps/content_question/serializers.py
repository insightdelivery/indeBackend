"""
콘텐츠 질문·답변 시리얼라이저
"""
from rest_framework import serializers
from .models import ContentQuestion, ContentQuestionAnswer


# ----- Admin -----

class ContentQuestionListSerializer(serializers.ModelSerializer):
    """관리자: 질문 목록 (목록/조회용)"""
    class Meta:
        model = ContentQuestion
        fields = [
            'question_id', 'content_type', 'content_id', 'question_text',
            'sort_order', 'is_required', 'is_locked',
            'created_by', 'created_at', 'updated_at',
        ]


class ContentQuestionCreateSerializer(serializers.ModelSerializer):
    """관리자: 질문 등록"""
    class Meta:
        model = ContentQuestion
        fields = [
            'content_type', 'content_id', 'question_text',
            'sort_order', 'is_required',
        ]

    def validate_question_text(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('질문 내용을 입력해주세요.')
        return value.strip()

    def validate_content_type(self, value):
        if value not in ('ARTICLE', 'VIDEO', 'SEMINAR'):
            raise serializers.ValidationError('content_type은 ARTICLE, VIDEO, SEMINAR 중 하나여야 합니다.')
        return value


class ContentQuestionUpdateSerializer(serializers.ModelSerializer):
    """관리자: 질문 수정 (is_locked 시 서버에서 거부)"""
    class Meta:
        model = ContentQuestion
        fields = [
            'question_text', 'sort_order', 'is_required',
        ]

    def validate_question_text(self, value):
        if value is not None and not value.strip():
            raise serializers.ValidationError('질문 내용을 입력해주세요.')
        return value.strip() if value else value


# ----- Public (사용자용) -----

class ContentQuestionPublicSerializer(serializers.ModelSerializer):
    """공개: 콘텐츠 질문 목록 (question_id, question_text, sort_order)"""
    class Meta:
        model = ContentQuestion
        fields = ['question_id', 'question_text', 'sort_order']


class ContentQuestionAnswerCreateSerializer(serializers.Serializer):
    """공개: 질문 답변 등록 페이로드"""
    question_id = serializers.IntegerField()
    content_type = serializers.ChoiceField(choices=['ARTICLE', 'VIDEO', 'SEMINAR'])
    content_id = serializers.IntegerField()
    answer_text = serializers.CharField(allow_blank=False)

    def validate_answer_text(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('답변 내용을 입력해주세요.')
        return value.strip()
