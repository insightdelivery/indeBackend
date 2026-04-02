from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("admin_messages", "0002_messagesendernumber"),
    ]

    operations = [
        migrations.CreateModel(
            name="MessageTemplate",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "channel",
                    models.CharField(
                        choices=[("sms", "문자"), ("kakao", "카카오"), ("email", "이메일")],
                        db_index=True,
                        max_length=16,
                    ),
                ),
                ("template_name", models.CharField(max_length=120)),
                ("content", models.TextField()),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_by_id", models.CharField(blank=True, db_index=True, default="", max_length=15)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "message_templates", "ordering": ["-id"]},
        ),
        migrations.AddIndex(
            model_name="messagetemplate",
            index=models.Index(fields=["channel", "is_active"], name="idx_msg_tpl_channel_active"),
        ),
    ]
