# article_highlight 테이블·컬럼 COMMENT (articleHightlightPlan.md §1, models.Meta.db_table_comment)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('highlight', '0002_allow_hex_color'),
    ]

    operations = [
        migrations.AlterModelTableComment(
            name='articlehighlight',
            table_comment='아티클 본문 하이라이트(사용자 선택 구간 저장·복원). articleHightlightPlan.md §1',
        ),
        migrations.AlterField(
            model_name='articlehighlight',
            name='id',
            field=models.BigAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name='ID',
                db_comment='하이라이트 PK (문서 필드명 highlight_id). AUTO_INCREMENT',
            ),
        ),
        migrations.AlterField(
            model_name='articlehighlight',
            name='article',
            field=models.ForeignKey(
                db_column='article_id',
                db_comment='아티클 FK (Article.id)',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='highlights',
                to='articles.article',
                verbose_name='아티클',
            ),
        ),
        migrations.AlterField(
            model_name='articlehighlight',
            name='user',
            field=models.ForeignKey(
                db_column='user_id',
                db_comment='사용자 FK (IndeUser)',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='article_highlights',
                to='public_api.indeuser',
                verbose_name='사용자',
            ),
        ),
        migrations.AlterField(
            model_name='articlehighlight',
            name='highlight_group_id',
            field=models.BigIntegerField(
                db_comment='같은 드래그에서 생성된 하이라이트 묶음. 단일 문단이면 해당 레코드 id와 동일 값',
                verbose_name='하이라이트 그룹 ID',
            ),
        ),
        migrations.AlterField(
            model_name='articlehighlight',
            name='paragraph_index',
            field=models.IntegerField(
                db_comment='Article 본문 HTML에서 문단 위치(0부터)',
                verbose_name='문단 인덱스',
            ),
        ),
        migrations.AlterField(
            model_name='articlehighlight',
            name='highlight_text',
            field=models.TextField(
                db_comment='사용자가 선택한 정확한 텍스트',
                verbose_name='선택 텍스트',
            ),
        ),
        migrations.AlterField(
            model_name='articlehighlight',
            name='prefix_text',
            field=models.CharField(
                blank=True,
                db_comment='선택 텍스트 앞 문맥(복원·검증용)',
                default='',
                max_length=255,
                verbose_name='앞 문맥',
            ),
        ),
        migrations.AlterField(
            model_name='articlehighlight',
            name='suffix_text',
            field=models.CharField(
                blank=True,
                db_comment='선택 텍스트 뒤 문맥(복원·검증용)',
                default='',
                max_length=255,
                verbose_name='뒤 문맥',
            ),
        ),
        migrations.AlterField(
            model_name='articlehighlight',
            name='start_offset',
            field=models.IntegerField(
                db_comment='문단 기준 시작 위치(문자 오프셋)',
                verbose_name='문단 내 시작 offset',
            ),
        ),
        migrations.AlterField(
            model_name='articlehighlight',
            name='end_offset',
            field=models.IntegerField(
                db_comment='문단 기준 끝 위치(문자 오프셋)',
                verbose_name='문단 내 끝 offset',
            ),
        ),
        migrations.AlterField(
            model_name='articlehighlight',
            name='color',
            field=models.CharField(
                db_comment='색상 식별자 또는 헥사(#RRGGBB 등)',
                default='yellow',
                max_length=20,
                verbose_name='색상',
            ),
        ),
        migrations.AlterField(
            model_name='articlehighlight',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                db_comment='생성일시(저장 시각)',
                verbose_name='생성일시',
            ),
        ),
    ]
