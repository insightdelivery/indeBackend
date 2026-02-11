"""
아티클 모델
"""
from django.db import models
from django.utils import timezone as django_timezone


class Article(models.Model):
    """
    아티클 모델
    """
    # 기본 정보
    id = models.AutoField(primary_key=True, verbose_name='아티클 ID')
    title = models.CharField(max_length=500, verbose_name='제목')
    subtitle = models.CharField(max_length=500, null=True, blank=True, verbose_name='부제목')
    content = models.TextField(verbose_name='본문 내용')
    thumbnail = models.CharField(max_length=500, null=True, blank=True, verbose_name='썸네일 URL')
    
    # 분류 및 작성자
    category = models.CharField(max_length=50, verbose_name='카테고리 (sysCodeSid)')
    author = models.CharField(max_length=100, verbose_name='작성자')
    authorAffiliation = models.CharField(max_length=200, null=True, blank=True, verbose_name='작성자 소속')
    
    # 공개 설정
    visibility = models.CharField(
        max_length=50,
        verbose_name='공개 범위 (sysCodeSid)',
        help_text='all, free, paid, purchased 중 하나 또는 sysCodeSid'
    )
    status = models.CharField(
        max_length=50,
        default='draft',
        verbose_name='발행 상태 (sysCodeSid)',
        help_text='draft, published, private, scheduled, deleted 중 하나 또는 sysCodeSid'
    )
    isEditorPick = models.BooleanField(default=False, verbose_name='에디터 추천')
    
    # 통계 정보
    viewCount = models.IntegerField(default=0, verbose_name='조회수')
    rating = models.FloatField(null=True, blank=True, verbose_name='평점')
    commentCount = models.IntegerField(default=0, verbose_name='댓글 수')
    highlightCount = models.IntegerField(default=0, verbose_name='하이라이트 수')
    questionCount = models.IntegerField(default=0, verbose_name='질문 수')
    
    # 추가 정보
    tags = models.JSONField(default=list, blank=True, verbose_name='태그 목록')
    questions = models.JSONField(default=list, blank=True, verbose_name='질문 목록')
    previewLength = models.IntegerField(null=True, blank=True, default=50, verbose_name='미리보기 길이')
    scheduledAt = models.DateTimeField(null=True, blank=True, verbose_name='예약 발행 일시')
    
    # 삭제 정보 (소프트 삭제)
    deletedAt = models.DateTimeField(null=True, blank=True, verbose_name='삭제 일시')
    deletedBy = models.CharField(max_length=100, null=True, blank=True, verbose_name='삭제자')
    
    # 타임스탬프
    createdAt = models.DateTimeField(auto_now_add=True, verbose_name='생성 일시')
    updatedAt = models.DateTimeField(auto_now=True, verbose_name='수정 일시')
    
    class Meta:
        db_table = 'article'
        verbose_name = '아티클'
        verbose_name_plural = '아티클'
        ordering = ['-createdAt']
        indexes = [
            models.Index(fields=['category'], name='idx_article_category'),
            models.Index(fields=['status'], name='idx_article_status'),
            models.Index(fields=['visibility'], name='idx_article_visibility'),
            models.Index(fields=['createdAt'], name='idx_article_created'),
            models.Index(fields=['deletedAt'], name='idx_article_deleted'),
            models.Index(fields=['author'], name='idx_article_author'),
        ]
    
    def __str__(self):
        return f"{self.title} (ID: {self.id})"
    
    def soft_delete(self, deleted_by=None):
        """소프트 삭제"""
        self.status = 'deleted'
        self.deletedAt = django_timezone.now()
        if deleted_by:
            self.deletedBy = deleted_by
        self.save()
    
    def restore(self):
        """복구"""
        self.status = 'draft'
        self.deletedAt = None
        self.deletedBy = None
        self.save()
    
    @property
    def is_deleted(self):
        """삭제 여부 확인"""
        return self.deletedAt is not None or self.status == 'deleted'

