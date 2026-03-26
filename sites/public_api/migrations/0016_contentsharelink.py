# content_share_link — contentShareLinkCopy.md §2

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0015_content_ranking_category_hot'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentShareLink',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                (
                    'content_type',
                    models.CharField(
                        choices=[('ARTICLE', 'ARTICLE'), ('VIDEO', 'VIDEO'), ('SEMINAR', 'SEMINAR')],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ('content_id', models.BigIntegerField()),
                ('user_id', models.BigIntegerField(db_column='user_id', db_index=True)),
                ('short_code', models.CharField(max_length=12)),
                ('expired_at', models.DateTimeField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'content_share_link',
                'verbose_name': '콘텐츠 공유 링크',
                'verbose_name_plural': '콘텐츠 공유 링크',
            },
        ),
        migrations.AddConstraint(
            model_name='contentsharelink',
            constraint=models.UniqueConstraint(fields=('short_code',), name='uniq_short_code'),
        ),
        migrations.AddConstraint(
            model_name='contentsharelink',
            constraint=models.UniqueConstraint(
                fields=('user_id', 'content_type', 'content_id'),
                name='uniq_user_content',
            ),
        ),
        migrations.AddIndex(
            model_name='contentsharelink',
            index=models.Index(fields=['expired_at'], name='idx_expired_at'),
        ),
    ]
