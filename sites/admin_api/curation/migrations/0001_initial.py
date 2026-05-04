# curation_content — curationContentPlan.md §1

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='CurationContent',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                (
                    'title',
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name='관리자용 커스텀 제목',
                    ),
                ),
                (
                    'content_type',
                    models.CharField(
                        choices=[
                            ('ARTICLE', 'ARTICLE'),
                            ('VIDEO', 'VIDEO'),
                            ('SEMINAR', 'SEMINAR'),
                        ],
                        max_length=20,
                        verbose_name='콘텐츠 타입',
                    ),
                ),
                ('content_code', models.BigIntegerField(verbose_name='실제 콘텐츠 PK')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성')),
                ('is_exposed', models.BooleanField(default=False, verbose_name='노출 여부')),
                (
                    'exposure_start_datetime',
                    models.DateTimeField(blank=True, null=True, verbose_name='노출 시작'),
                ),
                (
                    'exposure_end_datetime',
                    models.DateTimeField(blank=True, null=True, verbose_name='노출 종료'),
                ),
                ('reg_datetime', models.DateTimeField(auto_now_add=True, verbose_name='등록일')),
                ('update_datetime', models.DateTimeField(auto_now=True, verbose_name='수정일')),
            ],
            options={
                'verbose_name': '큐레이션 콘텐츠',
                'verbose_name_plural': '큐레이션 콘텐츠',
                'db_table': 'curation_content',
                'ordering': ['-is_exposed', '-reg_datetime'],
            },
        ),
        migrations.AddConstraint(
            model_name='curationcontent',
            constraint=models.UniqueConstraint(
                fields=('content_type', 'content_code'),
                name='uniq_curation_content_type_code',
            ),
        ),
    ]
