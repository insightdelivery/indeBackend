from django.db import models


class MessageBatch(models.Model):
    TYPE_SMS = "sms"
    TYPE_KAKAO = "kakao"
    TYPE_EMAIL = "email"
    TYPE_CHOICES = [
        (TYPE_SMS, "문자"),
        (TYPE_KAKAO, "카카오"),
        (TYPE_EMAIL, "이메일"),
    ]

    STATUS_SCHEDULED = "scheduled"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "예약"),
        (STATUS_PROCESSING, "처리중"),
        (STATUS_COMPLETED, "완료"),
        (STATUS_FAILED, "실패"),
        (STATUS_CANCELED, "취소"),
    ]

    id = models.BigAutoField(primary_key=True)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, db_index=True)
    sender = models.CharField(max_length=120)
    title = models.CharField(max_length=200, blank=True, default="")
    content = models.TextField(blank=True, default="")
    total_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    fail_count = models.PositiveIntegerField(default=0)
    excluded_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, db_index=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    is_processed = models.BooleanField(default=False, db_index=True)
    request_snapshot = models.JSONField(default=dict, blank=True)
    result_snapshot = models.JSONField(default=dict, blank=True)
    api_response_logs = models.JSONField(default=list, blank=True)
    created_by_id = models.CharField(max_length=15, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "message_batch"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["type", "status"], name="idx_msg_batch_type_status"),
            models.Index(fields=["scheduled_at", "is_processed"], name="idx_msg_batch_sched_proc"),
        ]


class MessageDetail(models.Model):
    STATUS_SUCCESS = "success"
    STATUS_FAIL = "fail"
    STATUS_EXCLUDED = "excluded"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "성공"),
        (STATUS_FAIL, "실패"),
        (STATUS_EXCLUDED, "제외"),
    ]

    id = models.BigAutoField(primary_key=True)
    batch = models.ForeignKey(
        MessageBatch,
        on_delete=models.CASCADE,
        related_name="details",
        db_column="batch_id",
    )
    receiver_name = models.CharField(max_length=80, blank=True, default="")
    receiver_phone = models.CharField(max_length=30, blank=True, default="", db_index=True)
    receiver_email = models.CharField(max_length=255, blank=True, default="")
    template_id = models.BigIntegerField(null=True, blank=True)
    template_name = models.CharField(max_length=120, blank=True, default="")
    variables = models.JSONField(default=dict, blank=True)
    final_content = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, db_index=True)
    external_code = models.CharField(max_length=50, blank=True, default="")
    external_message = models.TextField(blank=True, default="")
    error_reason = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "message_detail"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["batch", "status"], name="idx_msg_detail_batch_status"),
        ]


class KakaoTemplate(models.Model):
    STATUS_APPROVED = "approved"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_APPROVED, "승인"),
        (STATUS_INACTIVE, "비활성"),
    ]

    id = models.BigAutoField(primary_key=True)
    template_code = models.CharField(max_length=80, unique=True)
    template_name = models.CharField(max_length=120)
    content = models.TextField()
    emtitle = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="알리고 알림톡 강조표기형 타이틀(emtitle_1)",
    )
    variables = models.JSONField(default=list, blank=True)
    buttons = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_APPROVED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kakao_templates"
        ordering = ["-id"]


class MessageSenderNumber(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "승인대기"),
        (STATUS_APPROVED, "승인완료"),
        (STATUS_REJECTED, "반려"),
    ]

    id = models.BigAutoField(primary_key=True)
    sender_number = models.CharField(max_length=30, unique=True)
    manager_name = models.CharField(max_length=120, blank=True, default="")
    comment = models.CharField(max_length=255, blank=True, default="")
    request_type = models.CharField(max_length=30, default="manual")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    reject_reason = models.CharField(max_length=255, blank=True, default="")
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_by_id = models.CharField(max_length=15, blank=True, default="", db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "message_sender_number"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["status", "deleted_at"], name="idx_sender_status_deleted"),
        ]


class MessageSenderEmail(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "승인대기"),
        (STATUS_APPROVED, "승인완료"),
        (STATUS_REJECTED, "반려"),
    ]

    id = models.BigAutoField(primary_key=True)
    sender_email = models.CharField(max_length=254, unique=True)
    manager_name = models.CharField(max_length=120, blank=True, default="")
    comment = models.CharField(max_length=255, blank=True, default="")
    request_type = models.CharField(max_length=30, default="manual")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    reject_reason = models.CharField(max_length=255, blank=True, default="")
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_by_id = models.CharField(max_length=15, blank=True, default="", db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "message_sender_email"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["status", "deleted_at"], name="idx_sender_email_status_del"),
        ]


class MessageTemplate(models.Model):
    CHANNEL_SMS = "sms"
    CHANNEL_KAKAO = "kakao"
    CHANNEL_EMAIL = "email"
    CHANNEL_CHOICES = [
        (CHANNEL_SMS, "문자"),
        (CHANNEL_KAKAO, "카카오"),
        (CHANNEL_EMAIL, "이메일"),
    ]

    id = models.BigAutoField(primary_key=True)
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES, db_index=True)
    template_name = models.CharField(max_length=120)
    content = models.TextField()
    is_active = models.BooleanField(default=True, db_index=True)
    created_by_id = models.CharField(max_length=15, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "message_templates"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["channel", "is_active"], name="idx_msg_tpl_channel_active"),
        ]
