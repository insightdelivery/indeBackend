# publicUserActivityLog.activityType — ENUM 잔존 시 SHARE 삽입 Data truncated(1265) 방지
# Django AlterField만으로 ENUM이 VARCHAR로 바뀌지 않은 DB 대비

from django.db import migrations


TABLE = '`publicUserActivityLog`'
COL = '`activityType`'


def widen_activity_type(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"""
            ALTER TABLE {TABLE} MODIFY COLUMN {COL} VARCHAR(20) NOT NULL
            COMMENT '사용자 행동 유형 (VIEW, RATING, BOOKMARK, SHARE 등)'
            """
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0016_contentsharelink'),
    ]

    operations = [
        migrations.RunPython(widen_activity_type, noop_reverse),
    ]
