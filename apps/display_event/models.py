from django.db import models


class DisplayEvent(models.Model):
    """
    Hero 등 노출 단위. eventBannerPlan.md
    DB 테이블명: event_banner. 모든 필드에 DB 코멘트(db_comment) 유지.
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
        db_comment="이벤트 배너 행 PK (자동 증가)",
    )
    event_type_code = models.CharField(
        max_length=15,
        db_index=True,
        db_comment="노출 구분. sysCode 부모 SYS26320B003 하위 sysCodeSid",
    )
    content_type_code = models.CharField(
        max_length=15,
        db_index=True,
        db_comment="연결 콘텐츠 유형. sysCode 부모 SYS26320B009 하위 sysCodeSid",
    )
    content_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_comment="내부 콘텐츠 논리 ID(content_type_code에 따른 대상 PK). 외부 링크만 사용 시 NULL",
    )
    title = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_comment="배너 제목. 비우면 서버에서 콘텐츠 제목 등으로 보강 가능",
    )
    subtitle = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        db_comment="부제",
    )
    image_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        db_comment="배너 이미지 URL. 비우면 서버에서 콘텐츠 썸네일 등으로 보강 가능",
    )
    link_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        db_comment="외부 링크 URL. content_id가 있으면 사용 불가·NULL (§7 상호배타)",
    )
    display_order = models.IntegerField(
        default=0,
        db_comment="동일 event_type_code 내 정렬 순서(오름차순)",
    )
    is_active = models.BooleanField(
        default=True,
        db_comment="노출 활성 여부",
    )
    start_at = models.DateTimeField(
        null=True,
        blank=True,
        db_comment="노출 시작 일시. NULL이면 제한 없음(즉시)",
    )
    end_at = models.DateTimeField(
        null=True,
        blank=True,
        db_comment="노출 종료 일시. NULL이면 제한 없음(무기한)",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_comment="생성 일시",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_comment="수정 일시",
    )

    class Meta:
        db_table = "event_banner"
        ordering = ["-is_active", "display_order", "-id"]
        indexes = [
            models.Index(fields=["event_type_code", "is_active", "display_order"]),
            models.Index(fields=["start_at", "end_at"]),
        ]

    def __str__(self):
        return f"DisplayEvent({self.id}) {self.event_type_code}"
