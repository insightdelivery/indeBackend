from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("video", "0003_video_speaker_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="video",
            name="speakerProfileImage",
            field=models.CharField(
                blank=True,
                help_text="S3 등 URL (관리자 크롭 업로드)",
                max_length=500,
                null=True,
                verbose_name="출연자 프로필 이미지 URL",
            ),
        ),
    ]
