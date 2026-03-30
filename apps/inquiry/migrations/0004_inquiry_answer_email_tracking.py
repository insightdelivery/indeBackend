from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inquiry", "0003_alter_inquiry_inquiry_type_syscode"),
    ]

    operations = [
        migrations.AddField(
            model_name="inquiry",
            name="answer_email_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="inquiry",
            name="answer_email_opened_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="inquiry",
            name="answer_email_track_token",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
