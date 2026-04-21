# Generated manually — 목록 집계 DISTINCT question_id 조회 보조

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content_question', '0002_contentquestion_idx_cq_content_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='contentquestionanswer',
            index=models.Index(
                fields=['content_type', 'content_id', 'question_id'],
                name='idx_cqa_content_question',
            ),
        ),
    ]
