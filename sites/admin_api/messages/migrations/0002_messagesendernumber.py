from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("admin_messages", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MessageSenderNumber",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("sender_number", models.CharField(max_length=30, unique=True)),
                ("request_type", models.CharField(default="manual", max_length=30)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "승인대기"), ("approved", "승인완료"), ("rejected", "반려")],
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
                "db_table": "message_sender_number",
                "ordering": ["-id"],
            },
        ),
        migrations.AddIndex(
            model_name="messagesendernumber",
            index=models.Index(fields=["status", "deleted_at"], name="idx_sender_status_deleted"),
        ),
    ]
