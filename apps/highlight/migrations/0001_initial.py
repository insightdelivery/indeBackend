# Article Highlight initial (articleHightlightPlan.md)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('articles', '0004_remove_article_questions'),
        ('public_api', '0002_indeuser_socialaccount'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArticleHighlight',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('highlight_group_id', models.BigIntegerField(verbose_name='하이라이트 그룹 ID')),
                ('paragraph_index', models.IntegerField(verbose_name='문단 인덱스')),
                ('highlight_text', models.TextField(verbose_name='선택 텍스트')),
                ('prefix_text', models.CharField(blank=True, default='', max_length=255, verbose_name='앞 문맥')),
                ('suffix_text', models.CharField(blank=True, default='', max_length=255, verbose_name='뒤 문맥')),
                ('start_offset', models.IntegerField(verbose_name='문단 내 시작 offset')),
                ('end_offset', models.IntegerField(verbose_name='문단 내 끝 offset')),
                ('color', models.CharField(choices=[('yellow', 'yellow'), ('green', 'green'), ('blue', 'blue'), ('pink', 'pink')], default='yellow', max_length=20, verbose_name='색상')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일시')),
                ('article', models.ForeignKey(db_column='article_id', on_delete=django.db.models.deletion.CASCADE, related_name='highlights', to='articles.article', verbose_name='아티클')),
                ('user', models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.CASCADE, related_name='article_highlights', to='public_api.indeuser', verbose_name='사용자')),
            ],
            options={
                'verbose_name': '아티클 하이라이트',
                'verbose_name_plural': '아티클 하이라이트',
                'db_table': 'article_highlight',
                'ordering': ['article', 'paragraph_index', 'start_offset'],
            },
        ),
        migrations.AddIndex(
            model_name='articlehighlight',
            index=models.Index(fields=['article', 'user'], name='idx_hl_article_user'),
        ),
        migrations.AddIndex(
            model_name='articlehighlight',
            index=models.Index(fields=['article'], name='idx_hl_article'),
        ),
        migrations.AddIndex(
            model_name='articlehighlight',
            index=models.Index(fields=['highlight_group_id'], name='idx_hl_group'),
        ),
    ]
