# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inquiry", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="inquiry",
            name="inquiry_type",
            field=models.CharField(
                choices=[
                    ("usage", "이용 문의"),
                    ("payment", "결제 문의"),
                    ("etc", "기타"),
                ],
                default="usage",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="inquiry",
            name="attachment",
            field=models.FileField(
                blank=True,
                max_length=512,
                null=True,
                upload_to="inquiry_attachments/%Y/%m/",
            ),
        ),
    ]
