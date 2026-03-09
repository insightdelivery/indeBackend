# Generated for userPublicActiviteLog.md - 라이브러리 사용자 활동 로그

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0007_publicmembership_withdraw_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='PublicUserActivityLog',
            fields=[
                ('public_user_activity_log_id', models.BigAutoField(db_column='publicUserActivityLogId', primary_key=True, serialize=False, verbose_name='사용자 활동 로그 PK')),
                ('content_type', models.CharField(choices=[('ARTICLE', '아티클'), ('VIDEO', '비디오'), ('SEMINAR', '세미나')], db_column='contentType', max_length=20, verbose_name='콘텐츠 타입')),
                ('content_code', models.CharField(db_column='contentCode', max_length=50, verbose_name='콘텐츠 고유 코드')),
                ('activity_type', models.CharField(choices=[('VIEW', '조회'), ('RATING', '별점'), ('BOOKMARK', '북마크')], db_column='activityType', max_length=20, verbose_name='사용자 행동 유형')),
                ('rating_value', models.SmallIntegerField(blank=True, db_column='ratingValue', null=True, verbose_name='별점 값 (1~5)')),
                ('ip_address', models.CharField(blank=True, db_column='ipAddress', max_length=45, null=True, verbose_name='접속 IP')),
                ('user_agent', models.CharField(blank=True, db_column='userAgent', max_length=500, null=True, verbose_name='브라우저 정보')),
                ('reg_date_time', models.DateTimeField(auto_now=True, db_column='regDateTime', verbose_name='기록 시간')),
                ('user', models.ForeignKey(db_column='userId', on_delete=models.deletion.CASCADE, related_name='activity_logs', to='public_api.publicmembership', verbose_name='회원 ID')),
            ],
            options={
                'db_table': 'publicUserActivityLog',
                'ordering': ['-reg_date_time'],
                'verbose_name': '공개 사용자 활동 로그',
                'verbose_name_plural': '공개 사용자 활동 로그',
            },
        ),
        migrations.AddIndex(
            model_name='publicuseractivitylog',
            index=models.Index(fields=['content_type', 'content_code'], name='idx_content'),
        ),
        migrations.AddIndex(
            model_name='publicuseractivitylog',
            index=models.Index(fields=['user'], name='idx_user'),
        ),
        migrations.AddIndex(
            model_name='publicuseractivitylog',
            index=models.Index(fields=['activity_type'], name='idx_activity'),
        ),
        migrations.AddIndex(
            model_name='publicuseractivitylog',
            index=models.Index(fields=['content_type', 'content_code', 'activity_type'], name='idx_content_activity'),
        ),
        migrations.AddIndex(
            model_name='publicuseractivitylog',
            index=models.Index(fields=['reg_date_time'], name='idx_regDateTime'),
        ),
        migrations.AddConstraint(
            model_name='publicuseractivitylog',
            constraint=models.UniqueConstraint(fields=('user', 'content_type', 'content_code', 'activity_type'), name='uq_user_content_activity'),
        ),
    ]
