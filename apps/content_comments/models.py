from __future__ import annotations

from django.db import models
from django.utils import timezone

from sites.public_api.models import PublicMemberShip


class ContentComment(models.Model):
    CONTENT_TYPE_ARTICLE = "ARTICLE"
    CONTENT_TYPE_VIDEO = "VIDEO"
    CONTENT_TYPE_SEMINAR = "SEMINAR"
    CONTENT_TYPE_CHOICES = [
        (CONTENT_TYPE_ARTICLE, "아티클"),
        (CONTENT_TYPE_VIDEO, "비디오"),
        (CONTENT_TYPE_SEMINAR, "세미나"),
    ]

    id = models.BigAutoField(primary_key=True, db_comment="댓글 PK")
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        db_index=True,
        db_comment="콘텐츠 유형 (ARTICLE/VIDEO/SEMINAR)",
    )
    content_id = models.BigIntegerField(db_index=True, db_comment="콘텐츠 PK (article.id 또는 video.id)")

    user = models.ForeignKey(
        PublicMemberShip,
        on_delete=models.PROTECT,
        related_name="content_comments",
        db_column="user_id",
        db_comment="작성자 publicMemberShip.member_sid",
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="replies",
        db_column="parent_id",
        db_comment="부모 댓글 PK (NULL=댓글, 값 있음=대댓글)",
    )
    depth = models.PositiveSmallIntegerField(default=1, db_comment="댓글 깊이 (1=댓글, 2=대댓글)")

    comment_text = models.TextField(db_comment="댓글 본문")

    is_deleted = models.BooleanField(default=False, db_comment="소프트 삭제 여부")
    deleted_at = models.DateTimeField(null=True, blank=True, db_comment="삭제 일시(soft delete)")
    deleted_by = models.ForeignKey(
        PublicMemberShip,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_content_comments",
        db_column="deleted_by",
        db_comment="삭제 수행자 publicMemberShip.member_sid (없으면 NULL)",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_comment="생성 일시")
    updated_at = models.DateTimeField(auto_now=True, db_comment="수정 일시")

    class Meta:
        db_table = "content_comments"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["content_type", "content_id", "created_at"], name="idx_cc_content"),
            models.Index(fields=["parent", "created_at"], name="idx_cc_parent"),
            models.Index(fields=["user", "created_at"], name="idx_cc_user"),
        ]

    @property
    def is_admin_comment(self) -> bool:
        try:
            return bool(self.user and self.user.is_staff)
        except Exception:
            return False

    def soft_delete(self, by: PublicMemberShip | None) -> None:
        if self.is_deleted:
            return
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = by if by else None
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])

