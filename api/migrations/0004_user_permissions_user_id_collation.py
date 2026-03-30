# user_permissions.user_id 와 adminMemberShip.memberShipSid collation 정합 (MySQL 1267 방지)

from django.db import migrations


def _mysql_resolve_table(cursor, lower_name: str):
    cursor.execute(
        """
        SELECT TABLE_NAME FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND LOWER(TABLE_NAME) = %s
        LIMIT 1
        """,
        [lower_name],
    )
    row = cursor.fetchone()
    return row[0] if row else None


def align_user_permissions_user_id_collation(apps, schema_editor):
    conn = schema_editor.connection
    if conn.vendor != "mysql":
        return
    with conn.cursor() as cursor:
        admin_tbl = _mysql_resolve_table(cursor, "adminmembership")
        if not admin_tbl:
            return
        cursor.execute(
            """
            SELECT CHARACTER_SET_NAME, COLLATION_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = 'memberShipSid'
            """,
            [admin_tbl],
        )
        row = cursor.fetchone()
        if not row or not row[0] or not row[1]:
            return
        charset, collation = row[0], row[1]

        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_permissions'
            """
        )
        if cursor.fetchone()[0] == 0:
            return

        cursor.execute(
            """
            SELECT COLLATION_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'user_permissions'
              AND COLUMN_NAME = 'user_id'
            """
        )
        cur_row = cursor.fetchone()
        if cur_row and cur_row[0] == collation:
            return

        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'user_permissions'
              AND CONSTRAINT_TYPE = 'FOREIGN KEY'
            """
        )
        fk_rows = cursor.fetchall()
        fk_names = [r[0] for r in fk_rows if r and r[0]]

        for fk_name in fk_names:
            cursor.execute(
                "ALTER TABLE `user_permissions` DROP FOREIGN KEY `{}`".format(fk_name)
            )

        # charset/collation은 information_schema에서 읽은 값만 사용 (SQL 인젝션 방지)
        # NOT NULL 은 CHARACTER SET/COLLATE 뒤에 둬야 MariaDB/MySQL 파서가 인식함
        cursor.execute(
            """
            ALTER TABLE `user_permissions`
            MODIFY COLUMN `user_id` VARCHAR(15) CHARACTER SET {charset} COLLATE {collation} NOT NULL
            """.format(
                charset=charset,
                collation=collation,
            )
        )

        cursor.execute(
            """
            ALTER TABLE `user_permissions`
            ADD CONSTRAINT `user_permissions_user_fk`
            FOREIGN KEY (`user_id`) REFERENCES `{}` (`memberShipSid`) ON DELETE CASCADE
            """.format(
                admin_tbl.replace("`", "``"),
            )
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_drop_legacy_director_editor_columns"),
    ]

    operations = [
        migrations.RunPython(align_user_permissions_user_id_collation, noop_reverse),
    ]
