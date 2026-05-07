from django.db import migrations


class Migration(migrations.Migration):
    """
    비디오/세미나에는 하이라이트 수 컬럼을 두지 않습니다.
    과거에 AddField(highlightCount)가 있었다면, 적용 전 환경과 ORM·DB를 맞추기 위해
    이 마이그레이션은 DB 작업 없이 통과만 합니다.
    (이미 컬럼이 있는 DB는 수동 DROP 또는 별도 마이그레이션으로 정리 가능)
    """

    dependencies = [
        ("video", "0007_video_published_at"),
    ]

    operations = []
