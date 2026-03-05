# Generated for publicUserWithdrawRules.md - Soft Delete (탈퇴) 필드

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0006_publicmembership_is_staff'),
    ]

    operations = [
        migrations.AddField(
            model_name='publicmembership',
            name='status',
            field=models.CharField(
                choices=[('ACTIVE', '정상'), ('WITHDRAW_REQUEST', '탈퇴 요청'), ('WITHDRAWN', '탈퇴 완료')],
                db_index=True,
                default='ACTIVE',
                max_length=20,
                verbose_name='회원 상태',
            ),
        ),
        migrations.AddField(
            model_name='publicmembership',
            name='withdraw_reason',
            field=models.TextField(blank=True, null=True, verbose_name='탈퇴 사유'),
        ),
        migrations.AddField(
            model_name='publicmembership',
            name='withdraw_detail_reason',
            field=models.TextField(blank=True, null=True, verbose_name='탈퇴 상세 사유'),
        ),
        migrations.AddField(
            model_name='publicmembership',
            name='withdraw_requested_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='탈퇴 요청일시'),
        ),
        migrations.AddField(
            model_name='publicmembership',
            name='withdraw_completed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='탈퇴 완료일시'),
        ),
        migrations.AddField(
            model_name='publicmembership',
            name='withdraw_ip',
            field=models.CharField(blank=True, max_length=45, null=True, verbose_name='탈퇴 요청 IP'),
        ),
        migrations.AddField(
            model_name='publicmembership',
            name='withdraw_user_agent',
            field=models.TextField(blank=True, null=True, verbose_name='탈퇴 요청 User-Agent'),
        ),
    ]
