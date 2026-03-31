from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("public_api", "0014_content_ranking_cache_and_share_activity"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContentComment",
            fields=[
                ("id", models.BigAutoField(db_comment="댓글 PK", primary_key=True, serialize=False)),
                ("content_type", models.CharField(choices=[("ARTICLE", "아티클"), ("VIDEO", "비디오"), ("SEMINAR", "세미나")], db_comment="콘텐츠 유형 (ARTICLE/VIDEO/SEMINAR)", db_index=True, max_length=20)),
                ("content_id", models.BigIntegerField(db_comment="콘텐츠 PK (article.id 또는 video.id)", db_index=True)),
                ("depth", models.PositiveSmallIntegerField(db_comment="댓글 깊이 (1=댓글, 2=대댓글)", default=1)),
                ("comment_text", models.TextField(db_comment="댓글 본문")),
                ("is_deleted", models.BooleanField(db_comment="소프트 삭제 여부", default=False)),
                ("deleted_at", models.DateTimeField(blank=True, db_comment="삭제 일시(soft delete)", null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_comment="생성 일시")),
                ("updated_at", models.DateTimeField(auto_now=True, db_comment="수정 일시")),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        db_comment="삭제 수행자 publicMemberShip.member_sid (없으면 NULL)",
                        db_column="deleted_by",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="deleted_content_comments",
                        to="public_api.publicmembership",
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        db_comment="부모 댓글 PK (NULL=댓글, 값 있음=대댓글)",
                        db_column="parent_id",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="replies",
                        to="content_comments.contentcomment",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        db_comment="작성자 publicMemberShip.member_sid",
                        db_column="user_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="content_comments",
                        to="public_api.publicmembership",
                    ),
                ),
            ],
            options={
                "db_table": "content_comments",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="contentcomment",
            index=models.Index(fields=["content_type", "content_id", "created_at"], name="idx_cc_content"),
        ),
        migrations.AddIndex(
            model_name="contentcomment",
            index=models.Index(fields=["parent", "created_at"], name="idx_cc_parent"),
        ),
        migrations.AddIndex(
            model_name="contentcomment",
            index=models.Index(fields=["user", "created_at"], name="idx_cc_user"),
        ),
    ]

