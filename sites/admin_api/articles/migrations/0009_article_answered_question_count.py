from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0008_article_bookmark_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='answeredQuestionCount',
            field=models.IntegerField(
                db_comment='답변이 1건 이상인 질문 수(question_id distinct). 질문당 여러 사용자 답변이 있어도 1로만 집계.',
                default=0,
                verbose_name='답변 완료 질문 수',
            ),
        ),
    ]
