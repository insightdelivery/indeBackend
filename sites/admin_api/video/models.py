"""
비디오/세미나 모델
"""
from django.db import models
from django.utils import timezone as django_timezone


class Video(models.Model):
    """
    비디오/세미나 콘텐츠 모델
    """
    # 기본 정보
    id = models.AutoField(primary_key=True, verbose_name='비디오 ID')
    contentType = models.CharField(
        max_length=20,
        verbose_name='콘텐츠 타입',
        help_text='video: 비디오, seminar: 세미나'
    )
    category = models.CharField(
        max_length=50,
        verbose_name='카테고리 (sysCodeSid)',
        help_text='인터뷰, 현장 토크쇼, 강연, 기타'
    )
    
    # 제목 및 설명
    title = models.CharField(max_length=500, verbose_name='제목')
    subtitle = models.CharField(max_length=500, null=True, blank=True, verbose_name='부제목')
    body = models.TextField(null=True, blank=True, verbose_name='본문 설명')
    
    # 미디어
    videoStreamId = models.CharField(max_length=100, null=True, blank=True, verbose_name='Cloudflare Stream 비디오 ID')
    videoUrl = models.CharField(max_length=1000, null=True, blank=True, verbose_name='영상 URL', help_text='YouTube/Vimeo URL (레거시 지원)')
    thumbnail = models.CharField(max_length=500, null=True, blank=True, verbose_name='썸네일 URL')
    
    # 인물 정보
    speaker = models.CharField(max_length=200, null=True, blank=True, verbose_name='출연자/강사')
    speakerAffiliation = models.CharField(max_length=200, null=True, blank=True, verbose_name='출연자 소속')
    editor = models.CharField(max_length=100, null=True, blank=True, verbose_name='에디터')
    director = models.CharField(max_length=100, null=True, blank=True, verbose_name='디렉터')
    
    # 공개 설정
    visibility = models.CharField(
        max_length=50,
        verbose_name='공개 범위 (sysCodeSid)',
        help_text='전체, 무료회원, 유료회원, 특정구매자'
    )
    status = models.CharField(
        max_length=50,
        default='private',
        verbose_name='상태 (sysCodeSid)',
        help_text='public: 공개, private: 비공개, scheduled: 예약, deleted: 삭제대기'
    )
    
    # 배지 및 기능
    isNewBadge = models.BooleanField(default=False, verbose_name='NEW 배지 표시')
    isMaterialBadge = models.BooleanField(default=False, verbose_name='자료 배지 표시')
    allowRating = models.BooleanField(default=True, verbose_name='별점 허용')
    allowComment = models.BooleanField(default=True, verbose_name='댓글 허용')
    
    # 통계 정보
    viewCount = models.IntegerField(default=0, verbose_name='조회수')
    rating = models.FloatField(null=True, blank=True, verbose_name='평점')
    commentCount = models.IntegerField(default=0, verbose_name='댓글 수')
    
    # 추가 정보
    tags = models.JSONField(default=list, blank=True, verbose_name='태그 목록')
    questions = models.JSONField(default=list, blank=True, verbose_name='적용 질문 (Q1, Q2)')
    attachments = models.JSONField(default=list, blank=True, verbose_name='첨부파일 목록 (강의 자료)')
    
    # 예약 발행
    scheduledAt = models.DateTimeField(null=True, blank=True, verbose_name='예약 발행 일시')
    
    # 삭제 정보 (소프트 삭제)
    deletedAt = models.DateTimeField(null=True, blank=True, verbose_name='삭제 일시')
    deletedBy = models.CharField(max_length=100, null=True, blank=True, verbose_name='삭제자')
    
    # 타임스탬프
    createdAt = models.DateTimeField(auto_now_add=True, verbose_name='생성 일시')
    updatedAt = models.DateTimeField(auto_now=True, verbose_name='수정 일시')
    
    class Meta:
        db_table = 'video'
        verbose_name = '비디오/세미나'
        verbose_name_plural = '비디오/세미나'
        ordering = ['-createdAt']
        indexes = [
            models.Index(fields=['contentType'], name='idx_video_content_type'),
            models.Index(fields=['category'], name='idx_video_category'),
            models.Index(fields=['status'], name='idx_video_status'),
            models.Index(fields=['visibility'], name='idx_video_visibility'),
            models.Index(fields=['createdAt'], name='idx_video_created'),
            models.Index(fields=['deletedAt'], name='idx_video_deleted'),
            models.Index(fields=['speaker'], name='idx_video_speaker'),
            models.Index(fields=['editor'], name='idx_video_editor'),
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
        self.status = 'private'
        self.deletedAt = None
        self.deletedBy = None
        self.save()
    
    @property
    def is_deleted(self):
        """삭제 여부 확인"""
        return self.deletedAt is not None or self.status == 'deleted'
    
    def get_display_id(self):
        """표시용 ID 생성 (V/S + YYYYMMDD + Sequence)"""
        prefix = 'V' if self.contentType == 'video' else 'S'
        date_str = self.createdAt.strftime('%Y%m%d')
        # ID를 6자리로 패딩
        sequence = str(self.id).zfill(6)
        return f"{prefix}{date_str}{sequence}"

