# Curation + CurationItem (다중 콘텐츠), 기존 curation_content 이관 후 삭제

import django.db.models.deletion
from django.db import migrations, models


def forwards(apps, schema_editor):
    Curation = apps.get_model('curation', 'Curation')
    CurationItem = apps.get_model('curation', 'CurationItem')
    Legacy = apps.get_model('curation', 'CurationContent')
    for o in Legacy.objects.all().order_by('id'):
        c = Curation(
            name=None,
            is_active=o.is_active,
            is_exposed=o.is_exposed,
            exposure_start_datetime=o.exposure_start_datetime,
            exposure_end_datetime=o.exposure_end_datetime,
        )
        c.save()
        CurationItem.objects.create(
            curation=c,
            content_type=o.content_type,
            content_code=o.content_code,
            custom_title=o.title,
            sort_order=0,
        )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('curation', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Curation',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                (
                    'name',
                    models.CharField(
                        blank=True,
                        help_text='관리자 화면 구분용 (메인 노출 문구와 무관)',
                        max_length=255,
                        null=True,
                        verbose_name='관리용 이름',
                    ),
                ),
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
                'verbose_name': '큐레이션',
                'verbose_name_plural': '큐레이션',
                'db_table': 'curation',
                'ordering': ['-is_exposed', '-reg_datetime'],
            },
        ),
        migrations.CreateModel(
            name='CurationItem',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
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
                (
                    'custom_title',
                    models.CharField(
                        blank=True,
                        help_text='비우면 원본 콘텐츠 제목 사용',
                        max_length=255,
                        null=True,
                        verbose_name='항목 커스텀 제목',
                    ),
                ),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='정렬(오름차순)')),
                (
                    'curation',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='items',
                        to='curation.curation',
                        verbose_name='큐레이션',
                    ),
                ),
            ],
            options={
                'verbose_name': '큐레이션 항목',
                'verbose_name_plural': '큐레이션 항목',
                'db_table': 'curation_item',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='curationitem',
            constraint=models.UniqueConstraint(
                fields=('curation', 'content_type', 'content_code'),
                name='uniq_curation_item_ref',
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.DeleteModel(
            name='CurationContent',
        ),
    ]
