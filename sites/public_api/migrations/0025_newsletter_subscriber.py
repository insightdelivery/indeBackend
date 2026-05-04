# Generated manually for newsLetterModelPlan.md §3-1

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0024_database_utf8mb4_unicode_ci'),
    ]

    operations = [
        migrations.CreateModel(
            name='NewsletterSubscriber',
            fields=[
                ('subscriber_id', models.BigAutoField(primary_key=True, serialize=False, verbose_name='구독자 PK')),
                (
                    'email',
                    models.EmailField(
                        help_text='저장·통합 시 lower+trim 권장',
                        max_length=255,
                        unique=True,
                        verbose_name='이메일',
                    ),
                ),
                ('name', models.CharField(blank=True, max_length=100, null=True, verbose_name='이름')),
                (
                    'signup_source',
                    models.CharField(
                        choices=[('WEB_MODAL', '웹 모달'), ('MEMBER_SIGNUP', '회원가입')],
                        default='WEB_MODAL',
                        max_length=40,
                        verbose_name='유입',
                    ),
                ),
                (
                    'member_id',
                    models.BigIntegerField(
                        blank=True,
                        help_text='publicMemberShip.member_sid, 비로그인이면 NULL',
                        null=True,
                        verbose_name='구독 시점 회원 PK',
                    ),
                ),
                ('agree_privacy', models.BooleanField(verbose_name='개인정보 처리 동의')),
                ('agree_marketing', models.BooleanField(verbose_name='광고성 정보 수신 동의')),
                (
                    'subscribe_status',
                    models.CharField(
                        choices=[('SUBSCRIBED', '구독'), ('UNSUBSCRIBED', '구독 취소')],
                        default='SUBSCRIBED',
                        max_length=20,
                        verbose_name='구독 상태',
                    ),
                ),
                ('agree_datetime', models.DateTimeField(blank=True, null=True, verbose_name='구독·재구독 확정 시각')),
                ('unsubscribe_datetime', models.DateTimeField(blank=True, null=True, verbose_name='구독 취소 확정 시각')),
                ('ip_address', models.CharField(blank=True, max_length=45, null=True, verbose_name='구독 요청 IP')),
                ('user_agent', models.TextField(blank=True, null=True, verbose_name='구독 요청 User-Agent')),
                (
                    'stibee_sync_status',
                    models.CharField(default='PENDING', max_length=20, verbose_name='스티비 동기화 상태'),
                ),
                (
                    'stibee_subscriber_id',
                    models.CharField(blank=True, max_length=255, null=True, verbose_name='스티비 구독자 식별자'),
                ),
                ('create_at', models.DateTimeField(auto_now_add=True, verbose_name='행 최초 등록 시각')),
                ('update_at', models.DateTimeField(auto_now=True, verbose_name='행 최종 수정 시각')),
            ],
            options={
                'verbose_name': '뉴스레터 구독자',
                'verbose_name_plural': '뉴스레터 구독자',
                'db_table': 'newsletter_subscriber',
                'ordering': ['-create_at'],
            },
        ),
        migrations.AddIndex(
            model_name='newslettersubscriber',
            index=models.Index(fields=['create_at'], name='idx_newsletter_create_at'),
        ),
        migrations.AddIndex(
            model_name='newslettersubscriber',
            index=models.Index(fields=['member_id'], name='idx_newsletter_member_id'),
        ),
    ]
