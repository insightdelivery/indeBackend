from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("admin_messages", "0003_messagetemplate"),
    ]

    operations = [
        migrations.AddField(
            model_name="messagesendernumber",
            name="manager_name",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="messagesendernumber",
            name="comment",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
