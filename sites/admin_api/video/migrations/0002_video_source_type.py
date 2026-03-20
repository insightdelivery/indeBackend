# 0001은 RunPython만 있어 프로젝트 상태에 Video 모델이 없음 → AddField는 KeyError.
# DB: RunPython으로 sourceType 컬럼만 추가. 상태: CreateModel로 Video 전체(컬럼·인덱스) 등록.

from django.db import migrations, models


def add_source_type_column_and_backfill(apps, schema_editor):
    conn = schema_editor.connection
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES LIKE 'video'")
        if not cursor.fetchone():
            return

        cursor.execute("DESCRIBE `video`")
        columns = {row[0] for row in cursor.fetchall()}
        if "sourceType" in columns:
            return

        cursor.execute(
            """
            ALTER TABLE `video`
            ADD COLUMN `sourceType` VARCHAR(20) NOT NULL DEFAULT 'FILE_UPLOAD'
            COMMENT '영상 소스: FILE_UPLOAD, VIMEO, YOUTUBE'
            AFTER `videoUrl`
            """
        )

        cursor.execute(
            """
            UPDATE `video`
            SET `sourceType` = 'FILE_UPLOAD'
            WHERE `videoStreamId` IS NOT NULL AND TRIM(`videoStreamId`) <> ''
            """
        )

        cursor.execute(
            """
            UPDATE `video`
            SET `sourceType` = 'YOUTUBE'
            WHERE TRIM(IFNULL(`videoStreamId`, '')) = ''
            AND `videoUrl` IS NOT NULL AND TRIM(`videoUrl`) <> ''
            AND (
                LOWER(`videoUrl`) LIKE '%youtube.com%'
                OR LOWER(`videoUrl`) LIKE '%youtu.be%'
            )
            """
        )

        cursor.execute(
            """
            UPDATE `video`
            SET `sourceType` = 'VIMEO'
            WHERE TRIM(IFNULL(`videoStreamId`, '')) = ''
            AND `videoUrl` IS NOT NULL AND TRIM(`videoUrl`) <> ''
            AND LOWER(`videoUrl`) LIKE '%vimeo.com%'
            AND `sourceType` = 'FILE_UPLOAD'
            """
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("video", "0001_sync_video_schema"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_source_type_column_and_backfill, noop_reverse),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="Video",
                    fields=[
                        (
                            "id",
                            models.AutoField(
                                primary_key=True,
                                serialize=False,
                                verbose_name="비디오 ID",
                            ),
                        ),
                        (
                            "contentType",
                            models.CharField(
                                help_text="video: 비디오, seminar: 세미나",
                                max_length=20,
                                verbose_name="콘텐츠 타입",
                            ),
                        ),
                        (
                            "category",
                            models.CharField(
                                help_text="인터뷰, 현장 토크쇼, 강연, 기타",
                                max_length=50,
                                verbose_name="카테고리 (sysCodeSid)",
                            ),
                        ),
                        ("title", models.CharField(max_length=500, verbose_name="제목")),
                        (
                            "subtitle",
                            models.CharField(
                                blank=True,
                                max_length=500,
                                null=True,
                                verbose_name="부제목",
                            ),
                        ),
                        (
                            "body",
                            models.TextField(blank=True, null=True, verbose_name="본문 설명"),
                        ),
                        (
                            "videoStreamId",
                            models.CharField(
                                blank=True,
                                max_length=100,
                                null=True,
                                verbose_name="Cloudflare Stream 비디오 ID",
                            ),
                        ),
                        (
                            "videoUrl",
                            models.CharField(
                                blank=True,
                                help_text="YouTube/Vimeo URL (레거시 지원)",
                                max_length=1000,
                                null=True,
                                verbose_name="영상 URL",
                            ),
                        ),
                        (
                            "sourceType",
                            models.CharField(
                                default="FILE_UPLOAD",
                                help_text="FILE_UPLOAD: Cloudflare Stream, VIMEO, YOUTUBE",
                                max_length=20,
                                verbose_name="영상 소스 유형",
                            ),
                        ),
                        (
                            "thumbnail",
                            models.CharField(
                                blank=True,
                                max_length=500,
                                null=True,
                                verbose_name="썸네일 URL",
                            ),
                        ),
                        (
                            "speaker",
                            models.CharField(
                                blank=True,
                                max_length=200,
                                null=True,
                                verbose_name="출연자/강사",
                            ),
                        ),
                        (
                            "speakerAffiliation",
                            models.CharField(
                                blank=True,
                                max_length=200,
                                null=True,
                                verbose_name="출연자 소속",
                            ),
                        ),
                        (
                            "editor",
                            models.CharField(
                                blank=True,
                                max_length=100,
                                null=True,
                                verbose_name="에디터",
                            ),
                        ),
                        (
                            "director",
                            models.CharField(
                                blank=True,
                                max_length=100,
                                null=True,
                                verbose_name="디렉터",
                            ),
                        ),
                        (
                            "visibility",
                            models.CharField(
                                help_text="전체, 무료회원, 유료회원, 특정구매자",
                                max_length=50,
                                verbose_name="공개 범위 (sysCodeSid)",
                            ),
                        ),
                        (
                            "status",
                            models.CharField(
                                default="private",
                                help_text="public: 공개, private: 비공개, scheduled: 예약, deleted: 삭제대기",
                                max_length=50,
                                verbose_name="상태 (sysCodeSid)",
                            ),
                        ),
                        (
                            "isNewBadge",
                            models.BooleanField(default=False, verbose_name="NEW 배지 표시"),
                        ),
                        (
                            "isMaterialBadge",
                            models.BooleanField(default=False, verbose_name="자료 배지 표시"),
                        ),
                        (
                            "allowRating",
                            models.BooleanField(default=True, verbose_name="별점 허용"),
                        ),
                        (
                            "allowComment",
                            models.BooleanField(default=True, verbose_name="댓글 허용"),
                        ),
                        ("viewCount", models.IntegerField(default=0, verbose_name="조회수")),
                        (
                            "rating",
                            models.FloatField(blank=True, null=True, verbose_name="평점"),
                        ),
                        (
                            "commentCount",
                            models.IntegerField(default=0, verbose_name="댓글 수"),
                        ),
                        (
                            "tags",
                            models.JSONField(blank=True, default=list, verbose_name="태그 목록"),
                        ),
                        (
                            "questions",
                            models.JSONField(
                                blank=True,
                                default=list,
                                verbose_name="적용 질문 (Q1, Q2)",
                            ),
                        ),
                        (
                            "attachments",
                            models.JSONField(
                                blank=True,
                                default=list,
                                verbose_name="첨부파일 목록 (강의 자료)",
                            ),
                        ),
                        (
                            "scheduledAt",
                            models.DateTimeField(
                                blank=True, null=True, verbose_name="예약 발행 일시"
                            ),
                        ),
                        (
                            "deletedAt",
                            models.DateTimeField(
                                blank=True, null=True, verbose_name="삭제 일시"
                            ),
                        ),
                        (
                            "deletedBy",
                            models.CharField(
                                blank=True,
                                max_length=100,
                                null=True,
                                verbose_name="삭제자",
                            ),
                        ),
                        (
                            "createdAt",
                            models.DateTimeField(
                                auto_now_add=True, verbose_name="생성 일시"
                            ),
                        ),
                        (
                            "updatedAt",
                            models.DateTimeField(auto_now=True, verbose_name="수정 일시"),
                        ),
                    ],
                    options={
                        "verbose_name": "비디오/세미나",
                        "verbose_name_plural": "비디오/세미나",
                        "db_table": "video",
                        "ordering": ["-createdAt"],
                        "indexes": [
                            models.Index(
                                fields=["contentType"],
                                name="idx_video_content_type",
                            ),
                            models.Index(fields=["category"], name="idx_video_category"),
                            models.Index(fields=["status"], name="idx_video_status"),
                            models.Index(
                                fields=["visibility"],
                                name="idx_video_visibility",
                            ),
                            models.Index(fields=["createdAt"], name="idx_video_created"),
                            models.Index(fields=["deletedAt"], name="idx_video_deleted"),
                            models.Index(fields=["speaker"], name="idx_video_speaker"),
                            models.Index(fields=["editor"], name="idx_video_editor"),
                        ],
                    },
                ),
            ],
        ),
    ]
