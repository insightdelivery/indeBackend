from django.db import migrations, models

_STATUS_DRAFT = "SYS26209B022"
_STATUS_PUBLISHED = "SYS26209B021"
_STATUS_PRIVATE = "SYS26209B023"
_STATUS_SCHEDULED = "SYS26209B024"
_STATUS_DELETED = "SYS26209B025"

_VIDEO_LITERAL_MAP = (
    ("public", _STATUS_PUBLISHED),
    ("private", _STATUS_PRIVATE),
    ("scheduled", _STATUS_SCHEDULED),
    ("deleted", _STATUS_DELETED),
    ("draft", _STATUS_DRAFT),
)


def forwards_video_status_literals_to_sid(apps, schema_editor):
    Video = apps.get_model("video", "Video")
    for old, new in _VIDEO_LITERAL_MAP:
        Video.objects.filter(status=old).update(status=new)


def reverse_video_status_sid_to_literals(apps, schema_editor):
    Video = apps.get_model("video", "Video")
    rev = {new: old for old, new in _VIDEO_LITERAL_MAP}
    for new_sid, old_lit in rev.items():
        Video.objects.filter(status=new_sid).update(status=old_lit)


class Migration(migrations.Migration):

    dependencies = [
        ("video", "0004_video_speaker_profile_image"),
    ]

    operations = [
        migrations.RunPython(forwards_video_status_literals_to_sid, reverse_video_status_sid_to_literals),
        migrations.AlterField(
            model_name="video",
            name="status",
            field=models.CharField(
                default=_STATUS_PRIVATE,
                help_text="아티클 발행상태와 동일 SID 집합(SYS26209B020 하위, 예: SYS26209B021~025)",
                max_length=50,
                verbose_name="상태 (sysCodeSid)",
            ),
        ),
    ]
