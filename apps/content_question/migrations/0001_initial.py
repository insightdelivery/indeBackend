# content_question, content_question_answer 테이블 생성

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ContentQuestion',
            fields=[
                ('question_id', models.BigAutoField(db_column='question_id', primary_key=True, serialize=False, verbose_name='질문 고유 ID')),
                ('content_type', models.CharField(choices=[('ARTICLE', '아티클'), ('VIDEO', '비디오'), ('SEMINAR', '세미나')], db_column='content_type', max_length=20, verbose_name='콘텐츠 유형')),
                ('content_id', models.BigIntegerField(db_column='content_id', verbose_name='해당 콘텐츠 ID')),
                ('question_text', models.TextField(db_column='question_text', verbose_name='질문 내용')),
                ('sort_order', models.IntegerField(db_column='sort_order', default=0, verbose_name='질문 표시 순서')),
                ('is_required', models.BooleanField(db_column='is_required', default=True, verbose_name='필수 질문 여부')),
                ('is_locked', models.BooleanField(db_column='is_locked', default=False, verbose_name='답변 등록 시 수정 금지')),
                ('created_by', models.BigIntegerField(blank=True, db_column='created_by', null=True, verbose_name='질문 등록 관리자 ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column='created_at', verbose_name='질문 생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, db_column='updated_at', verbose_name='질문 수정일')),
            ],
            options={
                'db_table': 'content_question',
                'ordering': ['sort_order', 'question_id'],
                'verbose_name': '콘텐츠 질문',
                'verbose_name_plural': '콘텐츠 질문',
            },
        ),
        migrations.CreateModel(
            name='ContentQuestionAnswer',
            fields=[
                ('answer_id', models.BigAutoField(db_column='answer_id', primary_key=True, serialize=False, verbose_name='답변 고유 ID')),
                ('content_type', models.CharField(choices=[('ARTICLE', '아티클'), ('VIDEO', '비디오'), ('SEMINAR', '세미나')], db_column='content_type', max_length=20, verbose_name='콘텐츠 유형')),
                ('content_id', models.BigIntegerField(db_column='content_id', verbose_name='콘텐츠 ID')),
                ('user_id', models.BigIntegerField(db_column='user_id', verbose_name='답변 작성 사용자 ID')),
                ('answer_text', models.TextField(db_column='answer_text', verbose_name='주관식 답변')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column='created_at', verbose_name='답변 작성일')),
                ('question', models.ForeignKey(db_column='question_id', on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='content_question.ContentQuestion', verbose_name='질문 ID')),
            ],
            options={
                'db_table': 'content_question_answer',
                'verbose_name': '콘텐츠 질문 답변',
                'verbose_name_plural': '콘텐츠 질문 답변',
            },
        ),
        migrations.AddConstraint(
            model_name='contentquestionanswer',
            constraint=models.UniqueConstraint(fields=('question', 'user_id'), name='unique_user_answer'),
        ),
    ]
