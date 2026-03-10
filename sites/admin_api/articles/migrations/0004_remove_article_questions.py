# Article.questions 제거 (콘텐츠 질문은 content_question 테이블로 이전)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0003_article_author_id_fk'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='article',
            name='questions',
        ),
    ]
