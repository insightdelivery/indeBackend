# Generated manually for PhoneSmsVerification

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0012_publicmembership_index_names'),
    ]

    operations = [
        migrations.CreateModel(
            name='PhoneSmsVerification',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('phone', models.CharField(db_index=True, max_length=20, verbose_name='정규화된 휴대폰')),
                ('code_hash', models.CharField(max_length=128, verbose_name='인증번호 해시')),
                ('expires_at', models.DateTimeField(db_index=True, verbose_name='만료 시각')),
                ('verified', models.BooleanField(default=False, verbose_name='인증 완료')),
                ('attempt_count', models.PositiveSmallIntegerField(default=0, verbose_name='검증 시도 횟수')),
                ('last_sent_at', models.DateTimeField(verbose_name='마지막 발송 시각')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': '휴대폰 SMS 인증',
                'verbose_name_plural': '휴대폰 SMS 인증',
                'db_table': 'phoneSmsVerification',
            },
        ),
    ]
