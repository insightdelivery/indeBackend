# Video.speaker_id FK → content_author (article author_id 와 동일 패턴)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content_author", "0001_initial"),
        ("video", "0002_video_source_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="video",
            name="speaker_id",
            field=models.ForeignKey(
                blank=True,
                db_column="speaker_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="videos_as_speaker",
                to="content_author.contentauthor",
                verbose_name="출연자/강사(콘텐츠 저자)",
            ),
        ),
        migrations.AddIndex(
            model_name="video",
            index=models.Index(fields=["speaker_id"], name="idx_video_speaker_id"),
        ),
    ]
