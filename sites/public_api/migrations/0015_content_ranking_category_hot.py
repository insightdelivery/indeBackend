# CATEGORY_HOT + category_code (schedulerContentPlan.md §C)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0014_content_ranking_cache_and_share_activity'),
    ]

    operations = [
        migrations.AddField(
            model_name='contentrankingcache',
            name='category_code',
            field=models.CharField(
                blank=True,
                db_column='category_code',
                max_length=50,
                null=True,
                verbose_name='카테고리(sysCodeSid), CATEGORY_HOT 전용',
            ),
        ),
        migrations.AlterField(
            model_name='contentrankingcache',
            name='ranking_type',
            field=models.CharField(
                choices=[
                    ('HOT', '핫한 아티클'),
                    ('SHARE', '공유 많은 아티클'),
                    ('CATEGORY_HOT', '카테고리별 인기'),
                ],
                db_column='ranking_type',
                max_length=30,
                verbose_name='랭킹 유형',
            ),
        ),
        migrations.AddIndex(
            model_name='contentrankingcache',
            index=models.Index(
                fields=['ranking_type', 'category_code', 'base_date', 'rank_order'],
                name='idx_cat_hot_lookup',
            ),
        ),
    ]
