# ContentRankingCache.ranking_type — WEEKLY_CROSS (schedulerContentPlan.md §E)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0019_content_ranking_recommended_choice'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contentrankingcache',
            name='ranking_type',
            field=models.CharField(
                choices=[
                    ('HOT', '핫한 아티클'),
                    ('SHARE', '공유 많은 아티클'),
                    ('CATEGORY_HOT', '카테고리별 인기'),
                    ('RECOMMENDED', '추천 아티클'),
                    ('WEEKLY_CROSS', '주간 인기(크로스 타입)'),
                ],
                db_column='ranking_type',
                max_length=30,
                verbose_name='랭킹 유형',
            ),
        ),
    ]
