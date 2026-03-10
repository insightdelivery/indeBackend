# Generated migration for Content Author models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ContentAuthor',
            fields=[
                ('author_id', models.AutoField(primary_key=True, serialize=False, verbose_name='저자 ID')),
                ('name', models.CharField(max_length=100, verbose_name='이름')),
                ('profile_image', models.CharField(blank=True, max_length=500, null=True, verbose_name='프로필 이미지 URL')),
                ('role', models.CharField(choices=[('DIRECTOR', '디렉터'), ('EDITOR', '에디터')], default='EDITOR', max_length=20, verbose_name='역할')),
                ('status', models.CharField(choices=[('ACTIVE', '활성'), ('INACTIVE', '비활성')], default='ACTIVE', max_length=20, verbose_name='상태')),
                ('member_ship_sid', models.CharField(blank=True, max_length=15, null=True, verbose_name='연결 관리자 SID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성 일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정 일시')),
            ],
            options={
                'verbose_name': '콘텐츠 저자',
                'verbose_name_plural': '콘텐츠 저자',
                'db_table': 'content_author',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ContentAuthorContentType',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('content_type', models.CharField(choices=[('ARTICLE', '아티클'), ('VIDEO', '비디오'), ('SEMINAR', '세미나')], max_length=20, verbose_name='콘텐츠 유형')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='content_types', to='content_author.contentauthor', verbose_name='저자')),
            ],
            options={
                'verbose_name': '저자 담당 콘텐츠 유형',
                'verbose_name_plural': '저자 담당 콘텐츠 유형',
                'db_table': 'content_author_content_type',
                'unique_together': {('author', 'content_type')},
            },
        ),
    ]
