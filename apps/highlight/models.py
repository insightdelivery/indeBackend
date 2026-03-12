"""
Article Highlight 모델 (articleHightlightPlan.md §1, §3)
- 공개 사이트 사용자가 아티클 본문에서 선택한 텍스트를 하이라이트로 저장·복원
"""
from django.db import models

class ArticleHighlight(models.Model):
    """
    아티클 하이라이트
    - article: 공개 API에서 조회 가능한 아티클
    - user: 공개 사이트 로그인 사용자(IndeUser)
    - highlight_group_id: 같은 드래그에서 생성된 묶음. 단일 문단이면 본 레코드의 highlight_id와 동일 값 저장
    - color: 색상 식별자(yellow/green/blue/pink) 또는 헥스값(#RRGGBB, #RRGGBBAA)
    """
    article = models.ForeignKey(
        'articles.Article',
        on_delete=models.CASCADE,
        related_name='highlights',
        db_column='article_id',
        verbose_name='아티클',
    )
    user = models.ForeignKey(
        'public_api.IndeUser',
        on_delete=models.CASCADE,
        related_name='article_highlights',
        db_column='user_id',
        verbose_name='사용자',
    )
    highlight_group_id = models.BigIntegerField(verbose_name='하이라이트 그룹 ID')
    paragraph_index = models.IntegerField(verbose_name='문단 인덱스')
    highlight_text = models.TextField(verbose_name='선택 텍스트')
    prefix_text = models.CharField(max_length=255, blank=True, default='', verbose_name='앞 문맥')
    suffix_text = models.CharField(max_length=255, blank=True, default='', verbose_name='뒤 문맥')
    start_offset = models.IntegerField(verbose_name='문단 내 시작 offset')
    end_offset = models.IntegerField(verbose_name='문단 내 끝 offset')
    color = models.CharField(max_length=20, default='yellow', verbose_name='색상')  # 식별자 또는 hex(#RRGGBB)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')

    class Meta:
        db_table = 'article_highlight'
        verbose_name = '아티클 하이라이트'
        verbose_name_plural = '아티클 하이라이트'
        indexes = [
            models.Index(fields=['article', 'user'], name='idx_hl_article_user'),
            models.Index(fields=['article'], name='idx_hl_article'),
            models.Index(fields=['highlight_group_id'], name='idx_hl_group'),
        ]
        ordering = ['article', 'paragraph_index', 'start_offset']

    def __str__(self):
        return f"Highlight {self.id} article={self.article_id} p={self.paragraph_index}"
