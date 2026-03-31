from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0005_article_allow_comment"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="sermonHighlight",
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name="말씀 돋보기",
                db_comment="아티클 본문 하단에 노출하는 말씀 돋보기 텍스트",
            ),
        ),
    ]

