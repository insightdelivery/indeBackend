from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('video', '0005_video_status_syscodes_only'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='bookmarkCount',
            field=models.IntegerField(default=0, verbose_name='북마크 수'),
        ),
    ]
