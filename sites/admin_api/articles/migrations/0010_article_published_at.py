# Generated manually for 발행 일시

from django.db import migrations, models

STATUS_PUBLISHED = "SYS26209B021"
STATUS_SCHEDULED = "SYS26209B024"


def backfill_published_at(apps, schema_editor):
    Article = apps.get_model("articles", "Article")
    for row in Article.objects.all().iterator():
        pa = None
        if row.status == STATUS_PUBLISHED:
            pa = row.scheduledAt or row.createdAt
        elif row.status == STATUS_SCHEDULED and row.scheduledAt:
            pa = row.scheduledAt
        if pa is not None:
            Article.objects.filter(pk=row.pk).update(publishedAt=pa)


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0009_article_answered_question_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="publishedAt",
            field=models.DateTimeField(
                blank=True,
                db_comment="즉시 공개 시 등록 시각, 예약 시 scheduledAt, 크론 공개 시 예약 시각",
                null=True,
                verbose_name="발행 일시",
            ),
        ),
        migrations.RunPython(backfill_published_at, migrations.RunPython.noop),
    ]
