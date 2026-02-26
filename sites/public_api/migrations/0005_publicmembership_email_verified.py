# PublicMemberShip 이메일 인증 여부 필드 추가

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0004_member_sid_autoincrement_sns_provider_uid'),
    ]

    operations = [
        migrations.AddField(
            model_name='publicmembership',
            name='email_verified',
            field=models.BooleanField(default=False, verbose_name='이메일 인증 여부'),
        ),
    ]
