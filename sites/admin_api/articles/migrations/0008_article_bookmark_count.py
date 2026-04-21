from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0007_article_status_syscodes_only'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='bookmarkCount',
            field=models.IntegerField(default=0, verbose_name='북마크 수'),
        ),
    ]
