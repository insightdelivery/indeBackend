# recommended_search 1행 시드 (wwwDocEtc.md §3)

from django.db import migrations


def seed_recommended_search(apps, schema_editor):
    HomepageDocInfo = apps.get_model('homepage_doc', 'HomepageDocInfo')
    HomepageDocInfo.objects.get_or_create(
        doc_type='recommended_search',
        defaults={
            'title': None,
            'body_html': '',
            'is_published': True,
        },
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('homepage_doc', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_recommended_search, noop),
    ]
