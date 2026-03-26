# 아이디 찾기 vs 회원가입 SMS 세션 분리 (purpose)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0020_content_ranking_weekly_cross'),
    ]

    operations = [
        migrations.AddField(
            model_name='phonesmsverification',
            name='purpose',
            field=models.CharField(
                choices=[('signup', '회원가입'), ('find_id', '아이디찾기')],
                db_index=True,
                default='signup',
                max_length=20,
                verbose_name='인증 목적',
            ),
        ),
    ]
