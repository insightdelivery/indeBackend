# Migration: Article에 ContentAuthor FK(author_id) 추가

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0002_alter_article_content'),
        ('content_author', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='author_id',
            field=models.ForeignKey(
                blank=True,
                db_column='author_id',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='articles',
                to='content_author.ContentAuthor',
                verbose_name='작성자(콘텐츠 저자)',
            ),
        ),
    ]
