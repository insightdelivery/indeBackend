# content_ranking_cache (schedulerContentPlan.md) + SHARE activityType (userPublicActiviteLog.md)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0013_phonesmsverification'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentRankingCache',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                (
                    'ranking_type',
                    models.CharField(
                        choices=[('HOT', '핫한 아티클'), ('SHARE', '공유 많은 아티클')],
                        db_column='ranking_type',
                        max_length=30,
                        verbose_name='랭킹 유형',
                    ),
                ),
                (
                    'content_type',
                    models.CharField(
                        choices=[
                            ('ARTICLE', '아티클'),
                            ('VIDEO', '비디오'),
                            ('SEMINAR', '세미나'),
                        ],
                        db_column='content_type',
                        max_length=20,
                        verbose_name='콘텐츠 타입',
                    ),
                ),
                (
                    'content_code',
                    models.CharField(db_column='content_code', max_length=50, verbose_name='콘텐츠 코드'),
                ),
                ('score', models.FloatField(default=0.0, verbose_name='집계 점수')),
                ('rank_order', models.IntegerField(verbose_name='표시 순서(1~)')),
                ('base_date', models.DateField(db_column='base_date', verbose_name='집계 기준일')),
                (
                    'created_at',
                    models.DateTimeField(auto_now_add=True, db_column='created_at', verbose_name='생성일시'),
                ),
                (
                    'updated_at',
                    models.DateTimeField(auto_now=True, db_column='updated_at', verbose_name='수정일시'),
                ),
            ],
            options={
                'verbose_name': '콘텐츠 랭킹 캐시',
                'verbose_name_plural': '콘텐츠 랭킹 캐시',
                'db_table': 'content_ranking_cache',
                'ordering': ['base_date', 'ranking_type', 'rank_order'],
            },
        ),
        migrations.AddConstraint(
            model_name='contentrankingcache',
            constraint=models.UniqueConstraint(
                fields=('ranking_type', 'content_type', 'content_code', 'base_date'),
                name='uniq_rank',
            ),
        ),
        migrations.AddIndex(
            model_name='contentrankingcache',
            index=models.Index(
                fields=['ranking_type', 'content_type', 'base_date', 'rank_order'],
                name='idx_lookup',
            ),
        ),
        migrations.AlterField(
            model_name='publicuseractivitylog',
            name='activity_type',
            field=models.CharField(
                choices=[
                    ('VIEW', '조회'),
                    ('RATING', '별점'),
                    ('BOOKMARK', '북마크'),
                    ('SHARE', '공유'),
                ],
                db_column='activityType',
                max_length=20,
                verbose_name='사용자 행동 유형',
            ),
        ),
    ]
