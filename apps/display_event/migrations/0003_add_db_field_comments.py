# Generated manually: 모든 컬럼에 DB 코멘트(MySQL/MariaDB COMMENT) 반영

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("display_event", "0002_alter_displayevent_table"),
    ]

    operations = [
        migrations.AlterField(
            model_name="displayevent",
            name="id",
            field=models.BigAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name="ID",
                db_comment="이벤트 배너 행 PK (자동 증가)",
            ),
        ),
        migrations.AlterField(
            model_name="displayevent",
            name="event_type_code",
            field=models.CharField(
                db_comment="노출 구분. sysCode 부모 SYS26320B003 하위 sysCodeSid",
                db_index=True,
                max_length=15,
            ),
        ),
        migrations.AlterField(
            model_name="displayevent",
            name="content_type_code",
            field=models.CharField(
                db_comment="연결 콘텐츠 유형. sysCode 부모 SYS26320B009 하위 sysCodeSid",
                db_index=True,
                max_length=15,
            ),
        ),
        migrations.AlterField(
            model_name="displayevent",
            name="content_id",
            field=models.BigIntegerField(
                blank=True,
                db_comment="내부 콘텐츠 논리 ID(content_type_code에 따른 대상 PK). 외부 링크만 사용 시 NULL",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="displayevent",
            name="title",
            field=models.CharField(
                blank=True,
                db_comment="배너 제목. 비우면 서버에서 콘텐츠 제목 등으로 보강 가능",
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="displayevent",
            name="subtitle",
            field=models.CharField(
                blank=True,
                db_comment="부제",
                max_length=500,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="displayevent",
            name="image_url",
            field=models.CharField(
                blank=True,
                db_comment="배너 이미지 URL. 비우면 서버에서 콘텐츠 썸네일 등으로 보강 가능",
                max_length=500,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="displayevent",
            name="link_url",
            field=models.CharField(
                blank=True,
                db_comment="외부 링크 URL. content_id가 있으면 사용 불가·NULL (§7 상호배타)",
                max_length=500,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="displayevent",
            name="display_order",
            field=models.IntegerField(
                db_comment="동일 event_type_code 내 정렬 순서(오름차순)",
                default=0,
            ),
        ),
        migrations.AlterField(
            model_name="displayevent",
            name="is_active",
            field=models.BooleanField(
                db_comment="노출 활성 여부",
                default=True,
            ),
        ),
        migrations.AlterField(
            model_name="displayevent",
            name="start_at",
            field=models.DateTimeField(
                blank=True,
                db_comment="노출 시작 일시. NULL이면 제한 없음(즉시)",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="displayevent",
            name="end_at",
            field=models.DateTimeField(
                blank=True,
                db_comment="노출 종료 일시. NULL이면 제한 없음(무기한)",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="displayevent",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                db_comment="생성 일시",
            ),
        ),
        migrations.AlterField(
            model_name="displayevent",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                db_comment="수정 일시",
            ),
        ),
    ]
