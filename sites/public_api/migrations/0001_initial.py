# Initial migration: publicMemberShip table (PublicMemberShip model)

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='PublicMemberShip',
            fields=[
                ('member_sid', models.CharField(editable=False, max_length=20, primary_key=True, serialize=False, verbose_name='회원 SID')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='이메일')),
                ('password', models.CharField(blank=True, max_length=255, null=True, verbose_name='비밀번호')),
                ('name', models.CharField(max_length=100, verbose_name='이름')),
                ('nickname', models.CharField(max_length=100, verbose_name='닉네임')),
                ('phone', models.CharField(max_length=20, verbose_name='휴대폰 번호')),
                ('position', models.CharField(blank=True, max_length=100, null=True, verbose_name='직분')),
                ('birth_year', models.IntegerField(blank=True, null=True, verbose_name='출생년도')),
                ('birth_month', models.IntegerField(blank=True, null=True, verbose_name='출생월')),
                ('birth_day', models.IntegerField(blank=True, null=True, verbose_name='출생일')),
                ('region_type', models.CharField(blank=True, choices=[('DOMESTIC', '국내'), ('FOREIGN', '해외')], max_length=10, null=True, verbose_name='지역 타입')),
                ('region_domestic', models.CharField(blank=True, max_length=100, null=True, verbose_name='국내 지역')),
                ('region_foreign', models.CharField(blank=True, max_length=100, null=True, verbose_name='해외 지역')),
                ('joined_via', models.CharField(choices=[('LOCAL', '로컬 가입'), ('KAKAO', '카카오'), ('NAVER', '네이버'), ('GOOGLE', '구글')], default='LOCAL', max_length=10, verbose_name='가입 경로')),
                ('newsletter_agree', models.BooleanField(default=False, verbose_name='뉴스레터 수신 동의')),
                ('profile_completed', models.BooleanField(default=True, verbose_name='프로필 완료 여부')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성화')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='마지막 로그인')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일시')),
            ],
            options={
                'verbose_name': '공개 회원',
                'verbose_name_plural': '공개 회원',
                'db_table': 'publicMemberShip',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='publicmembership',
            index=models.Index(fields=['email'], name='publicMembe_email_8b7b0d_idx'),
        ),
        migrations.AddIndex(
            model_name='publicmembership',
            index=models.Index(fields=['phone'], name='publicMembe_phone_2c8e8a_idx'),
        ),
        migrations.AddIndex(
            model_name='publicmembership',
            index=models.Index(fields=['joined_via'], name='publicMembe_joined__1a2b3c_idx'),
        ),
        migrations.AddIndex(
            model_name='publicmembership',
            index=models.Index(fields=['is_active'], name='publicMembe_is_acti_4d5e6f_idx'),
        ),
    ]
