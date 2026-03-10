"""
콘텐츠 저자(Content Author) 모델
연동 기준: author_id. author_code 없음.
member_ship_sid: adminMemberShip 테이블 고유 코드(연결 관리자), null 가능.
"""
from django.db import models


class ContentAuthor(models.Model):
    """
    콘텐츠 저자 마스터
    """
    ROLE_DIRECTOR = 'DIRECTOR'
    ROLE_EDITOR = 'EDITOR'
    ROLE_CHOICES = [
        (ROLE_DIRECTOR, '디렉터'),
        (ROLE_EDITOR, '에디터'),
    ]
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_INACTIVE = 'INACTIVE'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, '활성'),
        (STATUS_INACTIVE, '비활성'),
    ]

    author_id = models.AutoField(primary_key=True, verbose_name='저자 ID')
    name = models.CharField(max_length=100, verbose_name='이름')
    profile_image = models.CharField(max_length=500, null=True, blank=True, verbose_name='프로필 이미지 URL')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_EDITOR, verbose_name='역할')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, verbose_name='상태')
    # adminMemberShip 테이블의 고유 코드(memberShipSid). 연결 안 하면 null.
    member_ship_sid = models.CharField(max_length=15, null=True, blank=True, verbose_name='연결 관리자 SID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 일시')

    class Meta:
        db_table = 'content_author'
        verbose_name = '콘텐츠 저자'
        verbose_name_plural = '콘텐츠 저자'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} (ID: {self.author_id})"


class ContentAuthorContentType(models.Model):
    """
    저자–콘텐츠 유형 매핑
    한 저자가 여러 콘텐츠 유형(ARTICLE/VIDEO/SEMINAR) 담당 가능.
    """
    TYPE_ARTICLE = 'ARTICLE'
    TYPE_VIDEO = 'VIDEO'
    TYPE_SEMINAR = 'SEMINAR'
    CONTENT_TYPE_CHOICES = [
        (TYPE_ARTICLE, '아티클'),
        (TYPE_VIDEO, '비디오'),
        (TYPE_SEMINAR, '세미나'),
    ]

    id = models.AutoField(primary_key=True)
    author = models.ForeignKey(
        ContentAuthor,
        on_delete=models.CASCADE,
        related_name='content_types',
        verbose_name='저자'
    )
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, verbose_name='콘텐츠 유형')

    class Meta:
        db_table = 'content_author_content_type'
        verbose_name = '저자 담당 콘텐츠 유형'
        verbose_name_plural = '저자 담당 콘텐츠 유형'
        unique_together = [('author', 'content_type')]

    def __str__(self):
        return f"{self.author.name} - {self.get_content_type_display()}"
