from django.db import models


class Curation(models.Model):
    """
    큐레이션 묶음(한 특집 슬롯) — 하위에 여러 CurationItem(콘텐츠 참조).
    curationContentPlan.md §1 확장.
    """

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='관리용 이름',
        help_text='관리자 화면 구분용 (메인 노출 문구와 무관)',
    )
    is_active = models.BooleanField(default=True, verbose_name='활성')
    is_exposed = models.BooleanField(default=False, verbose_name='노출 여부')
    exposure_start_datetime = models.DateTimeField(null=True, blank=True, verbose_name='노출 시작')
    exposure_end_datetime = models.DateTimeField(null=True, blank=True, verbose_name='노출 종료')
    reg_datetime = models.DateTimeField(auto_now_add=True, verbose_name='등록일')
    update_datetime = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        db_table = 'curation'
        verbose_name = '큐레이션'
        verbose_name_plural = '큐레이션'
        ordering = ['-is_exposed', '-reg_datetime']

    def __str__(self):
        return self.name or f'Curation #{self.pk}'


class CurationItem(models.Model):
    """큐레이션에 포함되는 단일 콘텐츠 참조."""

    class ContentType(models.TextChoices):
        ARTICLE = 'ARTICLE', 'ARTICLE'
        VIDEO = 'VIDEO', 'VIDEO'
        SEMINAR = 'SEMINAR', 'SEMINAR'

    id = models.BigAutoField(primary_key=True)
    curation = models.ForeignKey(
        Curation,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='큐레이션',
    )
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices,
        verbose_name='콘텐츠 타입',
    )
    content_code = models.BigIntegerField(verbose_name='실제 콘텐츠 PK')
    custom_title = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='항목 커스텀 제목',
        help_text='비우면 원본 콘텐츠 제목 사용',
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name='정렬(오름차순)')

    class Meta:
        db_table = 'curation_item'
        verbose_name = '큐레이션 항목'
        verbose_name_plural = '큐레이션 항목'
        ordering = ['sort_order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['curation', 'content_type', 'content_code'],
                name='uniq_curation_item_ref',
            ),
        ]

    def __str__(self):
        return f'{self.content_type}:{self.content_code}'
