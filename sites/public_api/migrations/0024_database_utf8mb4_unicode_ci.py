# 스키마 문자셋·콜레이션을 utf8mb4 / utf8mb4_unicode_ci 로 통일 (MySQL 1267 방지)
#
# - MySQL 1832: CONVERT 시 FK가 걸린 컬럼은 FOREIGN_KEY_CHECKS=0 만으로도 막힐 수 있음
#   → information_schema 로 FK 정의를 읽어 전부 DROP 후 CONVERT, 이후 동일 정의로 ADD
# - ALTER DATABASE: 권한 없으면 무시
# - SQLite 등 비-MySQL 은 no-op
#
# DDL이 길어 atomic=False (Django 마이그레이션 트랜잭션과 분리)

from django.db import migrations


def _forward(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        return

    db_name = connection.settings_dict.get("NAME") or ""
    if not db_name:
        return

    qdb = connection.ops.quote_name(db_name)

    with connection.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        try:
            cursor.execute(
                """
                SELECT kcu.CONSTRAINT_NAME,
                       kcu.TABLE_NAME,
                       GROUP_CONCAT(kcu.COLUMN_NAME ORDER BY kcu.ORDINAL_POSITION),
                       kcu.REFERENCED_TABLE_NAME,
                       GROUP_CONCAT(kcu.REFERENCED_COLUMN_NAME ORDER BY kcu.ORDINAL_POSITION),
                       rc.UPDATE_RULE,
                       rc.DELETE_RULE
                FROM information_schema.KEY_COLUMN_USAGE kcu
                INNER JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
                  ON kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
                 AND kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
                 AND kcu.TABLE_SCHEMA = rc.CONSTRAINT_SCHEMA
                 AND kcu.TABLE_NAME = rc.TABLE_NAME
                WHERE kcu.TABLE_SCHEMA = DATABASE()
                  AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
                GROUP BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME, kcu.REFERENCED_TABLE_NAME,
                         rc.UPDATE_RULE, rc.DELETE_RULE
                """
            )
            fk_rows = list(cursor.fetchall())

            for cname, tname, cols_csv, reftable, refcols_csv, upd, ddel in fk_rows:
                tc = str(tname).replace("`", "``")
                cc = str(cname).replace("`", "``")
                cursor.execute(f"ALTER TABLE `{tc}` DROP FOREIGN KEY `{cc}`")

            try:
                cursor.execute(
                    f"ALTER DATABASE {qdb} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            except Exception:
                pass

            cursor.execute(
                """
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_TYPE = 'BASE TABLE'
                """
            )
            tables = [row[0] for row in cursor.fetchall() if row and row[0]]

            for raw in tables:
                safe = str(raw).replace("`", "``")
                cursor.execute(
                    f"ALTER TABLE `{safe}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )

            for cname, tname, cols_csv, reftable, refcols_csv, upd, ddel in fk_rows:
                cols = [c.strip() for c in str(cols_csv).split(",") if c.strip()]
                refcols = [c.strip() for c in str(refcols_csv).split(",") if c.strip()]
                if len(cols) != len(refcols):
                    continue
                col_list = ", ".join(f"`{c.replace('`', '``')}`" for c in cols)
                refcol_list = ", ".join(f"`{c.replace('`', '``')}`" for c in refcols)
                tt = str(tname).replace("`", "``")
                rt = str(reftable).replace("`", "``")
                cn = str(cname).replace("`", "``")
                upd_sql = str(upd or "RESTRICT").upper()
                ddel_sql = str(ddel or "RESTRICT").upper()
                cursor.execute(
                    f"ALTER TABLE `{tt}` ADD CONSTRAINT `{cn}` FOREIGN KEY ({col_list}) "
                    f"REFERENCES `{rt}` ({refcol_list}) ON UPDATE {upd_sql} ON DELETE {ddel_sql}"
                )
        finally:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


def _reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("public_api", "0023_sitevisitevent"),
    ]

    operations = [
        migrations.RunPython(_forward, _reverse),
    ]
