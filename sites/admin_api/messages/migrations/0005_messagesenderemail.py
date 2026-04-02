# Generated manually for MessageSenderEmail

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_messages", "0004_messagesendernumber_manager_comment"),
    ]

    operations = [
        migrations.CreateModel(
            name="MessageSenderEmail",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("sender_email", models.CharField(max_length=254, unique=True)),
                ("manager_name", models.CharField(blank=True, default="", max_length=120)),
                ("comment", models.CharField(blank=True, default="", max_length=255)),
                ("request_type", models.CharField(default="manual", max_length=30)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "승인대기"),
                            ("approved", "승인완료"),
                            ("rejected", "반려"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("reject_reason", models.CharField(blank=True, default="", max_length=255)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("created_by_id", models.CharField(blank=True, db_index=True, default="", max_length=15)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "message_sender_email",
                "ordering": ["-id"],
            },
        ),
        migrations.AddIndex(
            model_name="messagesenderemail",
            index=models.Index(fields=["status", "deleted_at"], name="idx_sender_email_status_del"),
        ),
    ]
