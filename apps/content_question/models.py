"""
콘텐츠별 질문·답변 모델
- content_question: 콘텐츠(ARTICLE/VIDEO/SEMINAR)별 질문
- content_question_answer: 사용자별 질문 답변 (한 사용자당 한 질문에 한 번만)
"""
from django.db import models


class ContentQuestion(models.Model):
    """콘텐츠별 질문"""
    CONTENT_TYPE_ARTICLE = 'ARTICLE'
    CONTENT_TYPE_VIDEO = 'VIDEO'
    CONTENT_TYPE_SEMINAR = 'SEMINAR'
    CONTENT_TYPE_CHOICES = [
        (CONTENT_TYPE_ARTICLE, '아티클'),
        (CONTENT_TYPE_VIDEO, '비디오'),
        (CONTENT_TYPE_SEMINAR, '세미나'),
    ]

    question_id = models.BigAutoField(primary_key=True, verbose_name='질문 고유 ID', db_column='question_id')
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        verbose_name='콘텐츠 유형',
        db_column='content_type',
    )
    content_id = models.BigIntegerField(verbose_name='해당 콘텐츠 ID', db_column='content_id')
    question_text = models.TextField(verbose_name='질문 내용', db_column='question_text')
    sort_order = models.IntegerField(default=0, verbose_name='질문 표시 순서', db_column='sort_order')
    is_required = models.BooleanField(default=True, verbose_name='필수 질문 여부', db_column='is_required')
    is_locked = models.BooleanField(default=False, verbose_name='답변 등록 시 수정 금지', db_column='is_locked')
    created_by = models.BigIntegerField(null=True, blank=True, verbose_name='질문 등록 관리자 ID', db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='질문 생성일', db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='질문 수정일', db_column='updated_at')

    class Meta:
        db_table = 'content_question'
        verbose_name = '콘텐츠 질문'
        verbose_name_plural = '콘텐츠 질문'
        ordering = ['sort_order', 'question_id']
        indexes = [
            models.Index(fields=['content_type', 'content_id'], name='idx_cq_content'),
        ]

    def __str__(self):
        return f"[{self.content_type}:{self.content_id}] {self.question_text[:50]}"


class ContentQuestionAnswer(models.Model):
    """사용자 질문 답변 (question_id + user_id 유일)"""
    CONTENT_TYPE_ARTICLE = 'ARTICLE'
    CONTENT_TYPE_VIDEO = 'VIDEO'
    CONTENT_TYPE_SEMINAR = 'SEMINAR'
    CONTENT_TYPE_CHOICES = [
        (CONTENT_TYPE_ARTICLE, '아티클'),
        (CONTENT_TYPE_VIDEO, '비디오'),
        (CONTENT_TYPE_SEMINAR, '세미나'),
    ]

    answer_id = models.BigAutoField(primary_key=True, verbose_name='답변 고유 ID', db_column='answer_id')
    question = models.ForeignKey(
        ContentQuestion,
        on_delete=models.CASCADE,
        related_name='answers',
        db_column='question_id',
        verbose_name='질문 ID',
    )
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        verbose_name='콘텐츠 유형',
        db_column='content_type',
    )
    content_id = models.BigIntegerField(verbose_name='콘텐츠 ID', db_column='content_id')
    user_id = models.BigIntegerField(verbose_name='답변 작성 사용자 ID', db_column='user_id')
    answer_text = models.TextField(verbose_name='주관식 답변', db_column='answer_text')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='답변 작성일', db_column='created_at')

    class Meta:
        db_table = 'content_question_answer'
        verbose_name = '콘텐츠 질문 답변'
        verbose_name_plural = '콘텐츠 질문 답변'
        constraints = [
            models.UniqueConstraint(
                fields=['question', 'user_id'],
                name='unique_user_answer',
            ),
        ]
        indexes = [
            models.Index(fields=['question_id'], name='idx_cqa_question'),
            models.Index(fields=['content_type', 'content_id'], name='idx_cqa_content'),
            models.Index(
                fields=['content_type', 'content_id', 'question_id'],
                name='idx_cqa_content_question',
            ),
        ]

    def __str__(self):
        return f"Q{self.question_id} U{self.user_id}"
