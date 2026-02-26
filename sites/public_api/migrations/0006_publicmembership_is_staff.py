# 공지/FAQ/문의 게시판 관리자 권한용

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0005_publicmembership_email_verified'),
    ]

    operations = [
        migrations.AddField(
            model_name='publicmembership',
            name='is_staff',
            field=models.BooleanField(default=False, verbose_name='관리자 여부'),
        ),
    ]
