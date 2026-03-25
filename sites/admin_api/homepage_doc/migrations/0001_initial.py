# 홈페이지 정적 문서 테이블 + 6행 시드 (wwwDocEtc.md §3)

from django.db import migrations, models


def seed_homepage_docs(apps, schema_editor):
    HomepageDocInfo = apps.get_model('homepage_doc', 'HomepageDocInfo')
    for dt in (
        'company_intro',
        'terms_of_service',
        'privacy_policy',
        'article_copyright',
        'video_copyright',
        'seminar_copyright',
    ):
        HomepageDocInfo.objects.get_or_create(
            doc_type=dt,
            defaults={
                'title': None,
                'body_html': '',
                'is_published': True,
            },
        )


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='HomepageDocInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('doc_type', models.CharField(db_index=True, max_length=32, unique=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('body_html', models.TextField()),
                ('is_published', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'homepage_doc_info',
                'ordering': ['doc_type'],
            },
        ),
        migrations.RunPython(seed_homepage_docs, unseed),
    ]
