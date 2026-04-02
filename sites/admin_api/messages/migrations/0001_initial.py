from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("api", "0004_user_permissions_user_id_collation"),
    ]

    operations = [
        migrations.CreateModel(
            name="KakaoTemplate",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("template_code", models.CharField(max_length=80, unique=True)),
                ("template_name", models.CharField(max_length=120)),
                ("content", models.TextField()),
                ("variables", models.JSONField(blank=True, default=list)),
                ("buttons", models.JSONField(blank=True, default=list)),
                (
                    "status",
                    models.CharField(
                        choices=[("approved", "승인"), ("inactive", "비활성")],
                        db_index=True,
                        default="approved",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "kakao_templates", "ordering": ["-id"]},
        ),
        migrations.CreateModel(
            name="MessageBatch",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("type", models.CharField(choices=[("sms", "문자"), ("kakao", "카카오"), ("email", "이메일")], db_index=True, max_length=16)),
                ("sender", models.CharField(max_length=120)),
                ("title", models.CharField(blank=True, default="", max_length=200)),
                ("content", models.TextField(blank=True, default="")),
                ("total_count", models.PositiveIntegerField(default=0)),
                ("success_count", models.PositiveIntegerField(default=0)),
                ("fail_count", models.PositiveIntegerField(default=0)),
                ("excluded_count", models.PositiveIntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("scheduled", "예약"),
                            ("processing", "처리중"),
                            ("completed", "완료"),
                            ("failed", "실패"),
                            ("canceled", "취소"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("scheduled_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("canceled_at", models.DateTimeField(blank=True, null=True)),
                ("is_processed", models.BooleanField(db_index=True, default=False)),
                ("request_snapshot", models.JSONField(blank=True, default=dict)),
                ("result_snapshot", models.JSONField(blank=True, default=dict)),
                ("api_response_logs", models.JSONField(blank=True, default=list)),
                ("created_by_id", models.CharField(blank=True, db_index=True, default="", max_length=15)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "message_batch", "ordering": ["-id"]},
        ),
        migrations.CreateModel(
            name="MessageDetail",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("receiver_name", models.CharField(blank=True, default="", max_length=80)),
                ("receiver_phone", models.CharField(blank=True, db_index=True, default="", max_length=30)),
                ("receiver_email", models.CharField(blank=True, default="", max_length=255)),
                ("template_id", models.BigIntegerField(blank=True, null=True)),
                ("template_name", models.CharField(blank=True, default="", max_length=120)),
                ("variables", models.JSONField(blank=True, default=dict)),
                ("final_content", models.TextField(blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        choices=[("success", "성공"), ("fail", "실패"), ("excluded", "제외")],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("external_code", models.CharField(blank=True, default="", max_length=50)),
                ("external_message", models.TextField(blank=True, default="")),
                ("error_reason", models.TextField(blank=True, default="")),
                ("sent_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "batch",
                    models.ForeignKey(
                        db_column="batch_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="details",
                        to="admin_messages.messagebatch",
                    ),
                ),
            ],
            options={"db_table": "message_detail", "ordering": ["id"]},
        ),
        migrations.AddIndex(
            model_name="messagebatch",
            index=models.Index(fields=["type", "status"], name="idx_msg_batch_type_status"),
        ),
        migrations.AddIndex(
            model_name="messagebatch",
            index=models.Index(fields=["scheduled_at", "is_processed"], name="idx_msg_batch_sched_proc"),
        ),
        migrations.AddIndex(
            model_name="messagedetail",
            index=models.Index(fields=["batch", "status"], name="idx_msg_detail_batch_status"),
        ),
    ]
