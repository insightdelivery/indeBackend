# userPublicActiviteLog.md: userId NOT NULL DEFAULT 0 (0=비로그인), viewCount, regDate, UNIQUE uniq_view
# Idempotent: 이미 컬럼/인덱스가 있으면 건너뜀 (이전 부분 적용 복구용)

from django.db import migrations, models

TABLE = 'publicUserActivityLog'


def _column_exists(cursor, table, col):
    cursor.execute(
        """
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (table, col),
    )
    return cursor.fetchone() is not None


def _index_exists(cursor, table, idx):
    cursor.execute(
        """
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s
        """,
        (table, idx),
    )
    return cursor.fetchone() is not None


def _constraint_exists(cursor, name):
    cursor.execute(
        """
        SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
        WHERE TABLE_SCHEMA = DATABASE() AND CONSTRAINT_NAME = %s
        """,
        (name,),
    )
    return cursor.fetchone() is not None


def _fk_name_for_user_id(cursor, table):
    cursor.execute(
        """
        SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = 'userId'
          AND REFERENCED_TABLE_NAME IS NOT NULL
        LIMIT 1
        """,
        (table,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def apply_idempotent(apps, schema_editor):
    from django.db import connection

    with connection.cursor() as c:
        # 1) viewCount 없으면 추가
        if not _column_exists(c, TABLE, 'viewCount'):
            c.execute(
                f"ALTER TABLE {TABLE} ADD COLUMN viewCount INT NOT NULL DEFAULT 1 "
                "COMMENT '조회 진입 횟수'"
            )
        # 2) regDate 없으면 추가 후 백필 및 NOT NULL
        if not _column_exists(c, TABLE, 'regDate'):
            c.execute(
                f"ALTER TABLE {TABLE} ADD COLUMN regDate DATE NULL "
                "COMMENT '로그 날짜(년-월-일)'"
            )
        c.execute(
            f"UPDATE {TABLE} SET regDate = DATE(regDateTime) WHERE regDate IS NULL"
        )
        c.execute(f"ALTER TABLE {TABLE} MODIFY COLUMN regDate DATE NOT NULL")
        # 3) userId → user_id(BIGINT) 전환
        has_user_id = _column_exists(c, TABLE, 'userId')
        has_user_id_new = _column_exists(c, TABLE, 'userId_new')
        if has_user_id and not has_user_id_new:
            c.execute(
                f"ALTER TABLE {TABLE} ADD COLUMN userId_new BIGINT NOT NULL DEFAULT 0 "
                "COMMENT '회원 ID (0=비로그인)'"
            )
            c.execute(f"UPDATE {TABLE} SET userId_new = userId")
            if _constraint_exists(c, 'uq_user_content_activity'):
                c.execute(
                    f"ALTER TABLE {TABLE} DROP INDEX uq_user_content_activity"
                )
            fk = _fk_name_for_user_id(c, TABLE)
            if fk:
                c.execute(f"ALTER TABLE {TABLE} DROP FOREIGN KEY {connection.ops.quote_name(fk)}")
            c.execute(f"ALTER TABLE {TABLE} DROP COLUMN userId")
            c.execute(
                f"ALTER TABLE {TABLE} CHANGE COLUMN userId_new userId BIGINT NOT NULL DEFAULT 0"
            )
        elif not has_user_id and has_user_id_new:
            c.execute(
                f"ALTER TABLE {TABLE} CHANGE COLUMN userId_new userId BIGINT NOT NULL DEFAULT 0"
            )
        elif has_user_id and has_user_id_new:
            if _constraint_exists(c, 'uq_user_content_activity'):
                c.execute(
                    f"ALTER TABLE {TABLE} DROP INDEX uq_user_content_activity"
                )
            fk = _fk_name_for_user_id(c, TABLE)
            if fk:
                c.execute(f"ALTER TABLE {TABLE} DROP FOREIGN KEY {connection.ops.quote_name(fk)}")
            c.execute(f"ALTER TABLE {TABLE} DROP COLUMN userId")
            c.execute(
                f"ALTER TABLE {TABLE} CHANGE COLUMN userId_new userId BIGINT NOT NULL DEFAULT 0"
            )
        # 4) 인덱스 정리
        if _index_exists(c, TABLE, 'idx_content_activity'):
            c.execute(f"ALTER TABLE {TABLE} DROP INDEX idx_content_activity")
        if _index_exists(c, TABLE, 'idx_regDateTime'):
            c.execute(f"ALTER TABLE {TABLE} DROP INDEX idx_regDateTime")
        if not _index_exists(c, TABLE, 'idx_user'):
            c.execute(f"ALTER TABLE {TABLE} ADD INDEX idx_user (userId)")
        if not _index_exists(c, TABLE, 'idx_regDate'):
            c.execute(f"ALTER TABLE {TABLE} ADD INDEX idx_regDate (regDate)")
        # 5) uniq_view 없으면 추가
        if not _constraint_exists(c, 'uniq_view'):
            c.execute(
                f"ALTER TABLE {TABLE} ADD UNIQUE KEY uniq_view "
                "(contentType, contentCode, activityType, userId, regDate)"
            )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0009_publicmembership_region_type_length'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(apply_idempotent, noop)],
            state_operations=[
                migrations.AddField(
                    model_name='publicuseractivitylog',
                    name='view_count',
                    field=models.IntegerField(
                        db_column='viewCount', default=1, verbose_name='조회 진입 횟수'
                    ),
                ),
                migrations.AddField(
                    model_name='publicuseractivitylog',
                    name='reg_date',
                    field=models.DateField(
                        db_column='regDate',
                        null=True,
                        verbose_name='로그 날짜(년-월-일)',
                    ),
                ),
                migrations.AlterField(
                    model_name='publicuseractivitylog',
                    name='reg_date',
                    field=models.DateField(
                        db_column='regDate', verbose_name='로그 날짜(년-월-일)'
                    ),
                ),
                migrations.AddField(
                    model_name='publicuseractivitylog',
                    name='user_id',
                    field=models.BigIntegerField(
                        db_column='userId',
                        default=0,
                        verbose_name='회원 ID (0=비로그인)',
                    ),
                ),
                migrations.RemoveConstraint(
                    model_name='publicuseractivitylog',
                    name='uq_user_content_activity',
                ),
                migrations.RemoveField(
                    model_name='publicuseractivitylog',
                    name='user',
                ),
                migrations.RemoveIndex(
                    model_name='publicuseractivitylog',
                    name='idx_content_activity',
                ),
                migrations.RemoveIndex(
                    model_name='publicuseractivitylog',
                    name='idx_regDateTime',
                ),
                migrations.AddIndex(
                    model_name='publicuseractivitylog',
                    index=models.Index(
                        fields=['user_id'], name='idx_user'
                    ),
                ),
                migrations.AddIndex(
                    model_name='publicuseractivitylog',
                    index=models.Index(
                        fields=['reg_date'], name='idx_regDate'
                    ),
                ),
                migrations.AddConstraint(
                    model_name='publicuseractivitylog',
                    constraint=models.UniqueConstraint(
                        fields=(
                            'content_type',
                            'content_code',
                            'activity_type',
                            'user_id',
                            'reg_date',
                        ),
                        name='uniq_view',
                    ),
                ),
            ],
        ),
    ]
