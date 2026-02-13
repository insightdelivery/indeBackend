#!/usr/bin/env python3
"""
video 테이블에 Cloudflare Stream 컬럼 동기화 스크립트

전체 migrate가 막힌 환경에서도 video 스키마만 안전하게 보정한다.
"""
import os
import sys
import django

# Django 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection


def sync_video_table():
    with connection.cursor() as cursor:
        # video 테이블 존재 확인
        cursor.execute("SHOW TABLES LIKE 'video'")
        if not cursor.fetchone():
            print("✗ video 테이블이 없습니다. 먼저 video 테이블을 생성하세요.")
            sys.exit(1)

        # 컬럼 정보 조회
        cursor.execute("DESCRIBE `video`")
        columns = {row[0]: row for row in cursor.fetchall()}

        # 1) videoStreamId 컬럼 추가
        if "videoStreamId" not in columns:
            cursor.execute(
                """
                ALTER TABLE `video`
                ADD COLUMN `videoStreamId` VARCHAR(100) NULL DEFAULT NULL
                COMMENT 'Cloudflare Stream 비디오 ID'
                AFTER `body`
                """
            )
            print("✓ videoStreamId 컬럼을 추가했습니다.")
        else:
            print("✓ videoStreamId 컬럼이 이미 존재합니다.")

        # 2) videoUrl nullable 보정 (레거시 지원)
        video_url = columns.get("videoUrl")
        if video_url:
            # DESCRIBE: Field, Type, Null, Key, Default, Extra
            is_nullable = video_url[2] == "YES"
            if not is_nullable:
                cursor.execute(
                    """
                    ALTER TABLE `video`
                    MODIFY COLUMN `videoUrl` VARCHAR(1000) NULL DEFAULT NULL
                    COMMENT '영상 URL (YouTube/Vimeo URL, 레거시 지원)'
                    """
                )
                print("✓ videoUrl 컬럼을 NULL 허용으로 변경했습니다.")
            else:
                print("✓ videoUrl 컬럼은 이미 NULL 허용입니다.")
        else:
            print("⚠ videoUrl 컬럼이 없습니다. 테이블 스키마를 확인하세요.")

    print("\n완료: video 테이블 스키마 동기화가 끝났습니다.")


if __name__ == "__main__":
    try:
        sync_video_table()
    except Exception as e:
        print(f"✗ 오류 발생: {e}")
        sys.exit(1)


