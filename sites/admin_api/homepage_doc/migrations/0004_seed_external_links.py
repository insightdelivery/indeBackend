from django.db import migrations


def seed_external_links(apps, schema_editor):
    HomepageDocInfo = apps.get_model('homepage_doc', 'HomepageDocInfo')
    HomepageDocInfo.objects.get_or_create(
        doc_type='external_links',
        defaults={
            'title': 'external_links',
            'body_html': '{"recruitUrl":"","partnershipUrl":""}',
            'is_published': True,
        },
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('homepage_doc', '0003_homepage_doc_info_db_comments'),
    ]

    operations = [
        migrations.RunPython(seed_external_links, noop),
    ]

