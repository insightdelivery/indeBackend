# Generated manually — adminUserPermissionsPlan
# DB에 이미 admin_role 등이 수동 반영된 경우 중복 DDL 방지 (조건부 적용)

from django.db import migrations, models
import django.db.models.deletion


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


def _mysql_column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        [table, column],
    )
    return cursor.fetchone()[0] > 0


def _mysql_table_exists(cursor, table: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """,
        [table],
    )
    return cursor.fetchone()[0] > 0


def apply_admin_menu_permissions_schema(apps, schema_editor):
    """이미 존재하는 객체는 건너뜀 (부분 적용·수동 DDL 호환)."""
    conn = schema_editor.connection
    if conn.vendor == "mysql":
        with conn.cursor() as cursor:
            admin_tbl = _mysql_resolve_table(cursor, "adminmembership")
            if admin_tbl and not _mysql_column_exists(cursor, admin_tbl, "admin_role"):
                cursor.execute(
                    "ALTER TABLE `{}` ADD COLUMN `admin_role` VARCHAR(20) NOT NULL DEFAULT 'editor'".format(
                        admin_tbl
                    )
                )

            if _mysql_table_exists(cursor, "user_permissions"):
                return

            if not admin_tbl:
                raise RuntimeError("adminMemberShip 테이블을 찾을 수 없습니다.")

            cursor.execute(
                """
                CREATE TABLE `user_permissions` (
                    `id` BIGINT NOT NULL AUTO_INCREMENT,
                    `menu_code` VARCHAR(20) NOT NULL,
                    `can_read` TINYINT(1) NOT NULL DEFAULT 1,
                    `can_write` TINYINT(1) NOT NULL DEFAULT 0,
                    `can_delete` TINYINT(1) NOT NULL DEFAULT 0,
                    `user_id` VARCHAR(15) NOT NULL,
                    PRIMARY KEY (`id`),
                    CONSTRAINT `uniq_user_menu_code` UNIQUE (`user_id`, `menu_code`),
                    KEY `user_perm_user_menu_idx` (`user_id`, `menu_code`),
                    CONSTRAINT `user_permissions_user_fk`
                        FOREIGN KEY (`user_id`) REFERENCES `{}` (`memberShipSid`) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """.format(
                    admin_tbl
                )
            )
        return

    if conn.vendor == "sqlite":
        with conn.cursor() as cursor:
            cursor.execute("PRAGMA table_info(adminMemberShip)")
            cols = {r[1] for r in cursor.fetchall()}
            if "admin_role" not in cols:
                cursor.execute(
                    "ALTER TABLE adminMemberShip ADD COLUMN admin_role VARCHAR(20) NOT NULL DEFAULT 'editor'"
                )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_permissions (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    menu_code VARCHAR(20) NOT NULL,
                    can_read INTEGER NOT NULL DEFAULT 1,
                    can_write INTEGER NOT NULL DEFAULT 0,
                    can_delete INTEGER NOT NULL DEFAULT 0,
                    user_id VARCHAR(15) NOT NULL REFERENCES adminMemberShip (memberShipSid) ON DELETE CASCADE,
                    UNIQUE (user_id, menu_code)
                )
                """
            )
            try:
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS user_perm_user_menu_idx ON user_permissions (user_id, menu_code)"
                )
            except Exception:
                pass
        return


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(apply_admin_menu_permissions_schema, noop_reverse),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="adminmembership",
                    name="admin_role",
                    field=models.CharField(
                        blank=True,
                        default="editor",
                        help_text="director | editor — 초기 user_permissions 템플릿용",
                        max_length=20,
                        verbose_name="관리자 역할",
                    ),
                ),
                migrations.AlterField(
                    model_name="adminmembership",
                    name="memberShipLevel",
                    field=models.IntegerField(default=2, verbose_name="회원 레벨"),
                ),
                migrations.CreateModel(
                    name="UserPermission",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("menu_code", models.CharField(max_length=20)),
                        ("can_read", models.BooleanField(default=True)),
                        ("can_write", models.BooleanField(default=False)),
                        ("can_delete", models.BooleanField(default=False)),
                        (
                            "user",
                            models.ForeignKey(
                                db_column="user_id",
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="menu_permissions",
                                to="api.adminmembership",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "관리자 메뉴 권한",
                        "verbose_name_plural": "관리자 메뉴 권한",
                        "db_table": "user_permissions",
                    },
                ),
                migrations.AddConstraint(
                    model_name="userpermission",
                    constraint=models.UniqueConstraint(
                        fields=("user", "menu_code"), name="uniq_user_menu_code"
                    ),
                ),
                migrations.AddIndex(
                    model_name="userpermission",
                    index=models.Index(
                        fields=["user", "menu_code"], name="user_perm_user_menu_idx"
                    ),
                ),
            ],
        ),
    ]
