from django.db import migrations, models


def add_created_at_if_missing(apps, schema_editor):
    """created_at 컬럼이 없을 때만 추가 (이미 있으면 무시)"""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'faq_faq' AND COLUMN_NAME = 'created_at'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "ALTER TABLE faq_faq ADD COLUMN created_at DATETIME NULL"
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('faq', '0001_initial'),
    ]

    operations = [
        # DB: 컬럼이 없을 때만 추가 (있으면 무시)
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(add_created_at_if_missing, noop_reverse)],
            state_operations=[
                migrations.AddField(
                    model_name='faq',
                    name='created_at',
                    field=models.DateTimeField(auto_now_add=True, blank=True, null=True),
                ),
            ],
        ),
    ]
