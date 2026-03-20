# publicMemberShip 인덱스 이름 정리 (sns·status)
# - publicMembe_sns_pro_67b518_idx -> publicMembe_sns_pro_idx
# - publicMemberShip_status_b2e04528 / publicMemberShip_status_idx -> publicMemberShip_status
# - publicMembe_status_c06b7f_idx -> publicMembe_status_idx
# 이미 목표 이름만 있으면 RENAME/CREATE 는 건너뜀.

from django.db import migrations, models


def _index_names_on_column(cursor, table: str, column: str):
    cursor.execute(
        """
        SELECT DISTINCT INDEX_NAME
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
          AND INDEX_NAME <> 'PRIMARY'
        """,
        [table, column],
    )
    return {row[0] for row in cursor.fetchall()}


def _has_index(cursor, table: str, name: str) -> bool:
    cursor.execute(
        """
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s AND INDEX_NAME = %s
        LIMIT 1
        """,
        [table, name],
    )
    return cursor.fetchone() is not None


def _rename_index(cursor, table: str, old: str, new: str) -> None:
    if old == new:
        return
    if not _has_index(cursor, table, old):
        return
    if _has_index(cursor, table, new):
        return
    cursor.execute(f"ALTER TABLE `{table}` RENAME INDEX `{old}` TO `{new}`")


def rename_publicmembership_indexes_forwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    table = 'publicMemberShip'
    with schema_editor.connection.cursor() as cursor:
        _rename_index(cursor, table, 'publicMembe_sns_pro_67b518_idx', 'publicMembe_sns_pro_idx')

        if not _has_index(cursor, table, 'publicMemberShip_status'):
            for old in ('publicMemberShip_status_b2e04528', 'publicMemberShip_status_idx'):
                _rename_index(cursor, table, old, 'publicMemberShip_status')
                if _has_index(cursor, table, 'publicMemberShip_status'):
                    break
            if not _has_index(cursor, table, 'publicMemberShip_status'):
                for n in sorted(_index_names_on_column(cursor, table, 'status')):
                    if n == 'publicMembe_status_idx':
                        continue
                    if n.startswith('publicMemberShip_status') and n != 'publicMemberShip_status':
                        _rename_index(cursor, table, n, 'publicMemberShip_status')
                        break

        _rename_index(cursor, table, 'publicMembe_status_c06b7f_idx', 'publicMembe_status_idx')

        if not _has_index(cursor, table, 'publicMembe_status_idx'):
            cursor.execute(
                f"CREATE INDEX `publicMembe_status_idx` ON `{table}` (`status`)"
            )


def rename_publicmembership_indexes_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0011_remove_publicuseractivitylog_idx_user_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    rename_publicmembership_indexes_forwards,
                    rename_publicmembership_indexes_noop,
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='publicmembership',
                    name='status',
                    field=models.CharField(
                        choices=[
                            ('ACTIVE', '정상'),
                            ('WITHDRAW_REQUEST', '탈퇴 요청'),
                            ('WITHDRAWN', '탈퇴 완료'),
                        ],
                        db_index=False,
                        default='ACTIVE',
                        max_length=20,
                        verbose_name='회원 상태',
                    ),
                ),
                migrations.RenameIndex(
                    model_name='publicmembership',
                    new_name='publicMembe_sns_pro_idx',
                    old_name='publicMembe_sns_pro_67b518_idx',
                ),
                migrations.RemoveIndex(
                    model_name='publicmembership',
                    name='publicMembe_status_c06b7f_idx',
                ),
                migrations.AddIndex(
                    model_name='publicmembership',
                    index=models.Index(fields=['status'], name='publicMemberShip_status'),
                ),
                migrations.AddIndex(
                    model_name='publicmembership',
                    index=models.Index(fields=['status'], name='publicMembe_status_idx'),
                ),
            ],
        ),
    ]
