# 사이트 방문 이벤트 (siteInputDataPlan.md)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("public_api", "0022_phonesmsverification_verified_at_profile_phone"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteVisitEvent",
            fields=[
                (
                    "site_visit_event_id",
                    models.BigAutoField(
                        db_column="siteVisitEventId",
                        primary_key=True,
                        serialize=False,
                        verbose_name="사이트 방문 이벤트 PK",
                    ),
                ),
                (
                    "occurred_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_column="occurredAt",
                        verbose_name="서버 기록 시각",
                    ),
                ),
                (
                    "visit_date",
                    models.DateField(db_column="visitDate", verbose_name="집계용 일자(로컬)"),
                ),
                (
                    "channel",
                    models.CharField(
                        choices=[("direct", "일반"), ("share_link", "공유 링크")],
                        db_column="channel",
                        max_length=20,
                        verbose_name="유입 채널",
                    ),
                ),
                (
                    "visitor_key",
                    models.CharField(
                        db_column="visitorKey",
                        max_length=40,
                        verbose_name="익명 방문자 키(UUID)",
                    ),
                ),
                (
                    "path",
                    models.CharField(
                        blank=True,
                        db_column="path",
                        default="",
                        max_length=400,
                        verbose_name="랜딩 path+query 일부",
                    ),
                ),
                (
                    "user_agent",
                    models.CharField(
                        blank=True,
                        db_column="userAgent",
                        default="",
                        max_length=200,
                        verbose_name="User-Agent 앞부분",
                    ),
                ),
                (
                    "ip_hash",
                    models.CharField(
                        blank=True,
                        db_column="ipHash",
                        default="",
                        max_length=64,
                        verbose_name="접속 IP 해시",
                    ),
                ),
            ],
            options={
                "verbose_name": "사이트 방문 이벤트",
                "verbose_name_plural": "사이트 방문 이벤트",
                "db_table": "siteVisitEvent",
                "ordering": ["-occurred_at"],
            },
        ),
        migrations.AddIndex(
            model_name="sitevisitevent",
            index=models.Index(fields=["visit_date"], name="idx_siteVisit_visitDate"),
        ),
        migrations.AddIndex(
            model_name="sitevisitevent",
            index=models.Index(fields=["visit_date", "channel"], name="idx_siteVisit_date_ch"),
        ),
    ]
