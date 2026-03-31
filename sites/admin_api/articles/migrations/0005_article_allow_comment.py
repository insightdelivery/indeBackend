from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0004_remove_article_questions"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="allowComment",
            field=models.BooleanField(default=True, verbose_name="댓글 허용", db_comment="댓글 허용 여부 (true=표시/작성 가능)"),
        ),
    ]

