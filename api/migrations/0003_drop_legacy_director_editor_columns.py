"""
이전 0002 초안에서 sysCodeManager/sysCode에 추가했을 수 있는 director_yn, editor_yn 컬럼 제거.
권한 템플릿은 sysCodeVal / sysCodeVal1 을 사용한다.
"""

from django.db import migrations


def drop_legacy_columns(apps, schema_editor):
    conn = schema_editor.connection
    if conn.vendor != "mysql":
        return
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT TABLE_NAME FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND LOWER(TABLE_NAME) IN ('syscodemanager', 'syscode')
            """
        )
        for (table_name,) in cursor.fetchall():
            for col in ("director_yn", "editor_yn"):
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
                    """,
                    [table_name, col],
                )
                if cursor.fetchone()[0] == 0:
                    continue
                cursor.execute("ALTER TABLE `{}` DROP COLUMN `{}`".format(table_name, col))


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_admin_menu_permissions"),
    ]

    operations = [
        migrations.RunPython(drop_legacy_columns, noop_reverse),
    ]
