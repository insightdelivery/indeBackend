# IndeUser, SocialAccount 테이블 추가 (모델과 마이그레이션 동기화)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='IndeUser',
            fields=[
                ('id', models.CharField(editable=False, max_length=15, primary_key=True, serialize=False, verbose_name='회원 ID')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='이메일')),
                ('password', models.CharField(blank=True, max_length=255, null=True, verbose_name='비밀번호')),
                ('name', models.CharField(blank=True, max_length=100, null=True, verbose_name='이름')),
                ('phone', models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name='전화번호')),
                ('position', models.CharField(blank=True, max_length=100, null=True, verbose_name='교회 직분')),
                ('birth_year', models.IntegerField(blank=True, null=True, verbose_name='출생년도')),
                ('birth_month', models.IntegerField(blank=True, null=True, verbose_name='출생월')),
                ('birth_day', models.IntegerField(blank=True, null=True, verbose_name='출생일')),
                ('region_type', models.CharField(blank=True, choices=[('DOMESTIC', '국내'), ('FOREIGN', '해외')], max_length=10, null=True, verbose_name='지역 타입')),
                ('region_domestic', models.CharField(blank=True, max_length=100, null=True, verbose_name='국내 지역')),
                ('region_foreign', models.CharField(blank=True, max_length=100, null=True, verbose_name='해외 지역')),
                ('profile_completed', models.BooleanField(default=False, verbose_name='프로필 완료 여부')),
                ('joined_via', models.CharField(choices=[('LOCAL', '로컬 가입'), ('KAKAO', '카카오'), ('NAVER', '네이버'), ('GOOGLE', '구글')], default='LOCAL', max_length=10, verbose_name='가입 경로')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성화 여부')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='마지막 로그인 시간')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일시')),
            ],
            options={
                'verbose_name': '웹사이트 회원',
                'verbose_name_plural': '웹사이트 회원',
                'db_table': 'indeUser',
            },
        ),
        migrations.CreateModel(
            name='SocialAccount',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('provider', models.CharField(choices=[('kakao', '카카오'), ('naver', '네이버'), ('google', '구글')], max_length=20, verbose_name='SNS 제공자')),
                ('provider_user_id', models.CharField(max_length=255, verbose_name='SNS 제공자의 사용자 ID')),
                ('email_from_provider', models.EmailField(blank=True, max_length=254, null=True, verbose_name='SNS 제공자로부터 받은 이메일')),
                ('connected_at', models.DateTimeField(auto_now_add=True, verbose_name='연동일시')),
                ('last_login_at', models.DateTimeField(blank=True, null=True, verbose_name='마지막 로그인 시간')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일시')),
                ('user', models.ForeignKey(on_delete=models.CASCADE, related_name='social_accounts', to='public_api.indeuser', verbose_name='사용자')),
            ],
            options={
                'verbose_name': 'SNS 연동 계정',
                'verbose_name_plural': 'SNS 연동 계정',
                'db_table': 'SocialAccount',
                'unique_together': {('provider', 'provider_user_id')},
            },
        ),
        migrations.AddIndex(
            model_name='indeuser',
            index=models.Index(fields=['email'], name='indeUser_email_idx'),
        ),
        migrations.AddIndex(
            model_name='indeuser',
            index=models.Index(fields=['phone'], name='indeUser_phone_idx'),
        ),
        migrations.AddIndex(
            model_name='indeuser',
            index=models.Index(fields=['joined_via'], name='indeUser_joined__idx'),
        ),
        migrations.AddIndex(
            model_name='indeuser',
            index=models.Index(fields=['profile_completed'], name='indeUser_profile_idx'),
        ),
        migrations.AddIndex(
            model_name='indeuser',
            index=models.Index(fields=['region_type'], name='indeUser_region__idx'),
        ),
        migrations.AddIndex(
            model_name='indeuser',
            index=models.Index(fields=['is_active'], name='indeUser_is_acti_idx'),
        ),
        migrations.AddIndex(
            model_name='indeuser',
            index=models.Index(fields=['created_at'], name='indeUser_created_idx'),
        ),
        migrations.AddIndex(
            model_name='socialaccount',
            index=models.Index(fields=['user_id'], name='SocialAccou_user_id_idx'),
        ),
        migrations.AddIndex(
            model_name='socialaccount',
            index=models.Index(fields=['provider'], name='SocialAccou_provide_idx'),
        ),
        migrations.AddIndex(
            model_name='socialaccount',
            index=models.Index(fields=['email_from_provider'], name='SocialAccou_email_f_idx'),
        ),
    ]
