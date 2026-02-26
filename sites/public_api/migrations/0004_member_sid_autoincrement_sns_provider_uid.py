# member_sid: VARCHAR -> INT AUTO_INCREMENT, SNS 고유 코드 필드 추가

from django.db import migrations, models


def apply_mysql_schema(apps, schema_editor):
    """MySQL: sns_provider_uid 추가, member_sid를 INT AUTO_INCREMENT로 변경, 인덱스 추가"""
    if schema_editor.connection.vendor != 'mysql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE publicMemberShip
            ADD COLUMN sns_provider_uid VARCHAR(255) NULL DEFAULT NULL
            COMMENT 'SNS 제공자 고유 회원 코드 (KAKAO/NAVER/GOOGLE 가입 시)'
            AFTER joined_via
        """)
        cursor.execute("""
            ALTER TABLE publicMemberShip
            MODIFY COLUMN member_sid INT NOT NULL AUTO_INCREMENT
            COMMENT '회원 SID (1부터 자동 증가, PK)'
        """)
        cursor.execute("""
            CREATE INDEX publicMembe_sns_pro_idx ON publicMemberShip (sns_provider_uid)
        """)


def reverse_mysql_schema(apps, schema_editor):
    """MySQL: 롤백 (기존 VARCHAR PK로 복원 시 기존 데이터 유실 가능)"""
    if schema_editor.connection.vendor != 'mysql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP INDEX publicMembe_sns_pro_idx ON publicMemberShip")
        cursor.execute("ALTER TABLE publicMemberShip MODIFY COLUMN member_sid VARCHAR(20) NOT NULL COMMENT '회원 SID'")
        cursor.execute("ALTER TABLE publicMemberShip DROP COLUMN sns_provider_uid")


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0003_remove_socialaccount_socialaccou_user_id_idx_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='publicmembership',
                    name='sns_provider_uid',
                    field=models.CharField(
                        blank=True,
                        help_text='KAKAO/NAVER/GOOGLE 가입 시 해당 제공자의 회원 고유 ID',
                        max_length=255,
                        null=True,
                        verbose_name='SNS 제공자 고유 회원 코드',
                    ),
                ),
                migrations.AlterField(
                    model_name='publicmembership',
                    name='member_sid',
                    field=models.AutoField(primary_key=True, serialize=False, verbose_name='회원 SID'),
                ),
                migrations.AddIndex(
                    model_name='publicmembership',
                    index=models.Index(fields=['sns_provider_uid'], name='publicMembe_sns_pro_idx'),
                ),
            ],
            database_operations=[
                migrations.RunPython(apply_mysql_schema, reverse_mysql_schema),
            ],
        ),
    ]
