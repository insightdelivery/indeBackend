# content_share_link.share_token — contentShareLinkCopy.md §10.15

import secrets

from django.db import migrations, models


def _gen_token():
    return secrets.token_hex(32)


def backfill_share_tokens(apps, schema_editor):
    ContentShareLink = apps.get_model('public_api', 'ContentShareLink')
    for obj in ContentShareLink.objects.all():
        if getattr(obj, 'share_token', None):
            continue
        for _ in range(200):
            t = _gen_token()
            if not ContentShareLink.objects.filter(share_token=t).exists():
                obj.share_token = t
                obj.save(update_fields=['share_token'])
                break


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0017_publicuseractivitylog_activitytype_varchar'),
    ]

    operations = [
        migrations.AddField(
            model_name='contentsharelink',
            name='share_token',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.RunPython(backfill_share_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='contentsharelink',
            name='share_token',
            field=models.CharField(max_length=64),
        ),
        migrations.AddConstraint(
            model_name='contentsharelink',
            constraint=models.UniqueConstraint(fields=('share_token',), name='uniq_share_token'),
        ),
    ]
