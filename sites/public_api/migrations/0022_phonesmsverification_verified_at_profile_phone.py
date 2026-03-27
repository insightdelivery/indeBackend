# PhoneSmsVerification.verified_at + purpose에 profile_phone (wwwMypage_userInfo §5.2)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0021_phonesmsverification_purpose'),
    ]

    operations = [
        migrations.AddField(
            model_name='phonesmsverification',
            name='verified_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='인증 완료 시각'),
        ),
        migrations.AlterField(
            model_name='phonesmsverification',
            name='purpose',
            field=models.CharField(
                choices=[
                    ('signup', '회원가입'),
                    ('find_id', '아이디찾기'),
                    ('profile_phone', '회원정보_휴대폰변경'),
                ],
                db_index=True,
                default='signup',
                max_length=20,
                verbose_name='인증 목적',
            ),
        ),
    ]
