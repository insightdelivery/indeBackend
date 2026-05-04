from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content_author', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='contentauthor',
            name='editor_intro',
            field=models.TextField(blank=True, default='', verbose_name='에디터 소개'),
        ),
    ]
