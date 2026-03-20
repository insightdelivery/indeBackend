#!/usr/bin/env python
"""
public_api 0007 마이그레이션을 migrate 없이 적용하는 스크립트.
- publicMemberShip 테이블에 탈퇴(Soft Delete) 관련 필드 추가.
- 반드시 가상환경을 활성화한 뒤 실행한다.

  cd backend
  source venv/bin/activate   # Windows: venv\\Scripts\\activate
  python apply_public_api_0007_standalone.py
"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

import django
django.setup()

from django.db import connection


def column_exists(cursor, table, column):
    if connection.vendor == "mysql":
        cursor.execute(
            "SELECT 1 FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
            (table, column),
        )
        return cursor.fetchone() is not None
    if connection.vendor == "sqlite":
        cursor.execute("PRAGMA table_info(%s)" % table)
        return any(row[1] == column for row in cursor.fetchall())
    return False


def migration_applied(cursor):
    cursor.execute(
        "SELECT 1 FROM django_migrations WHERE app = %s AND name = %s",
        ("public_api", "0007_publicmembership_withdraw_fields"),
    )
    return cursor.fetchone() is not None


def main():
    with connection.cursor() as cursor:
        if migration_applied(cursor):
            print("0007_publicmembership_withdraw_fields는 이미 적용되어 있습니다.")
            return 0

        table = "publicMemberShip"
        if connection.vendor == "mysql":
            fields_to_add = [
                ("status", "VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'"),
                ("withdraw_reason", "TEXT NULL"),
                ("withdraw_detail_reason", "TEXT NULL"),
                ("withdraw_requested_at", "DATETIME NULL"),
                ("withdraw_completed_at", "DATETIME NULL"),
                ("withdraw_ip", "VARCHAR(45) NULL"),
                ("withdraw_user_agent", "TEXT NULL"),
            ]
        else:
            fields_to_add = [
                ("status", "VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'"),
                ("withdraw_reason", "TEXT"),
                ("withdraw_detail_reason", "TEXT"),
                ("withdraw_requested_at", "DATETIME"),
                ("withdraw_completed_at", "DATETIME"),
                ("withdraw_ip", "VARCHAR(45)"),
                ("withdraw_user_agent", "TEXT"),
            ]

        for col_name, col_def in fields_to_add:
            if column_exists(cursor, table, col_name):
                print(f"{col_name} 컬럼이 이미 있습니다.")
            else:
                cursor.execute(
                    "ALTER TABLE publicMemberShip ADD COLUMN %s %s" % (col_name, col_def)
                )
                print(f"{col_name} 컬럼 추가 완료.")

        if connection.vendor == "mysql":
            cursor.execute(
                "SELECT 1 FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'publicMemberShip' AND INDEX_NAME = 'publicMemberShip_status'"
            )
            if cursor.fetchone() is None:
                cursor.execute("CREATE INDEX publicMemberShip_status ON publicMemberShip (status)")
                print("status 인덱스 생성 완료.")

        # django_migrations 기록
        if connection.vendor == "mysql":
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
                ("public_api", "0007_publicmembership_withdraw_fields"),
            )
        else:
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, datetime('now'))",
                ("public_api", "0007_publicmembership_withdraw_fields"),
            )
        print("django_migrations에 0007 기록 완료.")

    print("public_api 0007 (탈퇴 필드) 적용 완료.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
