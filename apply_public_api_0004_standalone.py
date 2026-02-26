#!/usr/bin/env python
"""
public_api 0004 마이그레이션을 migrate 없이 적용하는 스크립트.
- DB에 이미 테이블이 있고, migrate 시 post_migrate(auth_permission 등) 오류가 날 때 사용.
- publicMemberShip: member_sid -> INT AUTO_INCREMENT, sns_provider_uid 컬럼 추가.
- 실행: cd backend && source venv/bin/activate && DJANGO_SETTINGS_MODULE=config.settings.local python apply_public_api_0004_standalone.py
"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django
django.setup()

from django.db import connection


def column_exists(cursor, table, column):
    cursor.execute(
        "SELECT 1 FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (table, column),
    )
    return cursor.fetchone() is not None


def index_exists(cursor, table, index_name):
    cursor.execute(
        "SELECT 1 FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s",
        (table, index_name),
    )
    return cursor.fetchone() is not None


def column_type(cursor, table, column):
    cursor.execute(
        "SELECT DATA_TYPE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (table, column),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def migration_applied(cursor):
    cursor.execute(
        "SELECT 1 FROM django_migrations WHERE app = %s AND name = %s",
        ("public_api", "0004_member_sid_autoincrement_sns_provider_uid"),
    )
    return cursor.fetchone() is not None


def fix_content_type_name_nullable(cursor):
    """Django 5에서 제거된 name 컬럼이 NOT NULL이면 nullable로 변경 (post_migrate 오류 방지)"""
    cursor.execute(
        "SELECT IS_NULLABLE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'django_content_type' AND COLUMN_NAME = 'name'"
    )
    row = cursor.fetchone()
    if row and row[0] == "NO":
        print("django_content_type.name을 NULL 허용으로 변경 중...")
        cursor.execute(
            "ALTER TABLE django_content_type MODIFY COLUMN name VARCHAR(100) NULL DEFAULT NULL"
        )


def main():
    if connection.vendor != "mysql":
        print("MySQL이 아니면 스크립트를 건너뜁니다.")
        return 0

    with connection.cursor() as cursor:
        fix_content_type_name_nullable(cursor)
        if migration_applied(cursor):
            print("0004는 이미 적용되어 있습니다.")
            return 0

        table = "publicMemberShip"
        has_sns = column_exists(cursor, table, "sns_provider_uid")

        if not has_sns:
            print("sns_provider_uid 컬럼 추가 중...")
            cursor.execute("""
                ALTER TABLE publicMemberShip
                ADD COLUMN sns_provider_uid VARCHAR(255) NULL DEFAULT NULL
                COMMENT 'SNS 제공자 고유 회원 코드 (KAKAO/NAVER/GOOGLE 가입 시)'
                AFTER joined_via
            """)
        else:
            print("sns_provider_uid 컬럼이 이미 있습니다.")

        current_type = column_type(cursor, table, "member_sid")
        if current_type and current_type.upper() != "INT":
            print("member_sid를 INT AUTO_INCREMENT로 변경 중...")
            cursor.execute("""
                ALTER TABLE publicMemberShip
                MODIFY COLUMN member_sid INT NOT NULL AUTO_INCREMENT
                COMMENT '회원 SID (1부터 자동 증가, PK)'
            """)
        else:
            print("member_sid가 이미 INT입니다.")

        if not index_exists(cursor, table, "publicMembe_sns_pro_idx"):
            print("sns_provider_uid 인덱스 생성 중...")
            cursor.execute(
                "CREATE INDEX publicMembe_sns_pro_idx ON publicMemberShip (sns_provider_uid)"
            )
        else:
            print("인덱스가 이미 있습니다.")

        print("django_migrations에 0004 기록 중...")
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
            ("public_api", "0004_member_sid_autoincrement_sns_provider_uid"),
        )

    print("public_api 0004 적용 완료.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)
