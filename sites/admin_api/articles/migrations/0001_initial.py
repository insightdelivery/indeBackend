# Generated migration for Article model

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='아티클 ID')),
                ('title', models.CharField(max_length=500, verbose_name='제목')),
                ('subtitle', models.CharField(blank=True, max_length=500, null=True, verbose_name='부제목')),
                ('content', models.TextField(verbose_name='본문 내용')),
                ('thumbnail', models.CharField(blank=True, max_length=500, null=True, verbose_name='썸네일 URL')),
                ('category', models.CharField(max_length=50, verbose_name='카테고리 (sysCodeSid)')),
                ('author', models.CharField(max_length=100, verbose_name='작성자')),
                ('authorAffiliation', models.CharField(blank=True, max_length=200, null=True, verbose_name='작성자 소속')),
                ('visibility', models.CharField(help_text='all, free, paid, purchased 중 하나 또는 sysCodeSid', max_length=50, verbose_name='공개 범위 (sysCodeSid)')),
                ('status', models.CharField(default='draft', help_text='draft, published, private, scheduled, deleted 중 하나 또는 sysCodeSid', max_length=50, verbose_name='발행 상태 (sysCodeSid)')),
                ('isEditorPick', models.BooleanField(default=False, verbose_name='에디터 추천')),
                ('viewCount', models.IntegerField(default=0, verbose_name='조회수')),
                ('rating', models.FloatField(blank=True, null=True, verbose_name='평점')),
                ('commentCount', models.IntegerField(default=0, verbose_name='댓글 수')),
                ('highlightCount', models.IntegerField(default=0, verbose_name='하이라이트 수')),
                ('questionCount', models.IntegerField(default=0, verbose_name='질문 수')),
                ('tags', models.JSONField(blank=True, default=list, verbose_name='태그 목록')),
                ('questions', models.JSONField(blank=True, default=list, verbose_name='질문 목록')),
                ('previewLength', models.IntegerField(blank=True, default=50, null=True, verbose_name='미리보기 길이')),
                ('scheduledAt', models.DateTimeField(blank=True, null=True, verbose_name='예약 발행 일시')),
                ('deletedAt', models.DateTimeField(blank=True, null=True, verbose_name='삭제 일시')),
                ('deletedBy', models.CharField(blank=True, max_length=100, null=True, verbose_name='삭제자')),
                ('createdAt', models.DateTimeField(auto_now_add=True, verbose_name='생성 일시')),
                ('updatedAt', models.DateTimeField(auto_now=True, verbose_name='수정 일시')),
            ],
            options={
                'verbose_name': '아티클',
                'verbose_name_plural': '아티클',
                'db_table': 'article',
                'ordering': ['-createdAt'],
            },
        ),
        migrations.AddIndex(
            model_name='article',
            index=models.Index(fields=['category'], name='idx_article_category'),
        ),
        migrations.AddIndex(
            model_name='article',
            index=models.Index(fields=['status'], name='idx_article_status'),
        ),
        migrations.AddIndex(
            model_name='article',
            index=models.Index(fields=['visibility'], name='idx_article_visibility'),
        ),
        migrations.AddIndex(
            model_name='article',
            index=models.Index(fields=['createdAt'], name='idx_article_created'),
        ),
        migrations.AddIndex(
            model_name='article',
            index=models.Index(fields=['deletedAt'], name='idx_article_deleted'),
        ),
        migrations.AddIndex(
            model_name='article',
            index=models.Index(fields=['author'], name='idx_article_author'),
        ),
    ]

