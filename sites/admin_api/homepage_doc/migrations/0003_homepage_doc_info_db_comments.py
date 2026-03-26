# homepage_doc_info 컬럼 COMMENT (wwwDocEtc.md 기능 설명)

from django.db import migrations, models


def comment_on_id_mysql(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE `homepage_doc_info`
            MODIFY COLUMN `id` bigint NOT NULL AUTO_INCREMENT
            COMMENT '레코드 고유 ID (자동 증가 PK)'
            """
        )


def reverse_comment_on_id_mysql(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE `homepage_doc_info`
            MODIFY COLUMN `id` bigint NOT NULL AUTO_INCREMENT
            COMMENT ''
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ('homepage_doc', '0002_seed_recommended_search'),
    ]

    operations = [
        migrations.AlterField(
            model_name='homepagedocinfo',
            name='doc_type',
            field=models.CharField(
                db_comment='문서 종류 코드. 허용 7값만: company_intro(회사소개), terms_of_service(이용약관), privacy_policy(개인정보취급방침), article_copyright(아티클 저작권), video_copyright(비디오 저작권), seminar_copyright(세미나 저작권), recommended_search(추천검색어). 행당 UNIQUE.',
                db_index=True,
                max_length=32,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name='homepagedocinfo',
            name='title',
            field=models.CharField(
                blank=True,
                db_comment='www 페이지 제목·메타 등 표시용. NULL 허용. recommended_search는 관리자 저장 시 title=search 고정 관례.',
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='homepagedocinfo',
            name='body_html',
            field=models.TextField(
                db_comment='HTML 본문(빈 문자열 허용). 회사소개/약관/개인정보는 RichText, 저작권·추천검색어는 Textarea 반영. 이미지는 base64 DB 저장 금지 — 백엔드 PUT에서 S3 URL로 치환 후 저장.',
            ),
        ),
        migrations.AlterField(
            model_name='homepagedocinfo',
            name='is_published',
            field=models.BooleanField(
                db_comment='true일 때만 www 공개 GET(/api/homepage-docs/...)으로 노출. false면 404.',
                default=True,
            ),
        ),
        migrations.AlterField(
            model_name='homepagedocinfo',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_comment='생성 일시'),
        ),
        migrations.AlterField(
            model_name='homepagedocinfo',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_comment='최종 수정 일시'),
        ),
        migrations.RunPython(comment_on_id_mysql, reverse_comment_on_id_mysql),
    ]
