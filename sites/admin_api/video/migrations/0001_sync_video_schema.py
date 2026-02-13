from django.db import migrations


def sync_video_schema(apps, schema_editor):
    """
    Keep DB schema in sync with current Video model for environments where
    the table was created manually from SQL scripts.
    """
    conn = schema_editor.connection

    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES LIKE 'video'")
        if not cursor.fetchone():
            # Table does not exist in this DB yet. Skip safely.
            return

        cursor.execute("DESCRIBE `video`")
        columns = {row[0]: row for row in cursor.fetchall()}

        if "videoStreamId" not in columns:
            cursor.execute(
                """
                ALTER TABLE `video`
                ADD COLUMN `videoStreamId` VARCHAR(100) NULL DEFAULT NULL
                COMMENT 'Cloudflare Stream 비디오 ID'
                AFTER `body`
                """
            )

        video_url = columns.get("videoUrl")
        if video_url:
            # DESCRIBE result index: 2 -> Null ("YES" or "NO")
            is_nullable = video_url[2] == "YES"
            if not is_nullable:
                cursor.execute(
                    """
                    ALTER TABLE `video`
                    MODIFY COLUMN `videoUrl` VARCHAR(1000) NULL DEFAULT NULL
                    COMMENT '영상 URL (YouTube/Vimeo URL, 레거시 지원)'
                    """
                )


def noop_reverse(apps, schema_editor):
    # Schema rollback is intentionally skipped to avoid destructive changes.
    pass


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.RunPython(sync_video_schema, noop_reverse),
    ]


