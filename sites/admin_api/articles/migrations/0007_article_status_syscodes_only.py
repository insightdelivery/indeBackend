from django.db import migrations, models

# sites.admin_api.content_publish_syscodes 와 동일 (마이그레이션은 상수 임포트 회피)
_STATUS_DRAFT = "SYS26209B022"
_STATUS_PUBLISHED = "SYS26209B021"
_STATUS_PRIVATE = "SYS26209B023"
_STATUS_SCHEDULED = "SYS26209B024"
_STATUS_DELETED = "SYS26209B025"

_ARTICLE_LITERAL_MAP = (
    ("published", _STATUS_PUBLISHED),
    ("draft", _STATUS_DRAFT),
    ("private", _STATUS_PRIVATE),
    ("scheduled", _STATUS_SCHEDULED),
    ("deleted", _STATUS_DELETED),
)


def forwards_article_status_literals_to_sid(apps, schema_editor):
    Article = apps.get_model("articles", "Article")
    for old, new in _ARTICLE_LITERAL_MAP:
        Article.objects.filter(status=old).update(status=new)


def reverse_article_status_sid_to_literals(apps, schema_editor):
    Article = apps.get_model("articles", "Article")
    rev = {new: old for old, new in _ARTICLE_LITERAL_MAP}
    for new_sid, old_lit in rev.items():
        Article.objects.filter(status=new_sid).update(status=old_lit)


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0006_article_sermon_highlight"),
    ]

    operations = [
        migrations.RunPython(forwards_article_status_literals_to_sid, reverse_article_status_sid_to_literals),
        migrations.AlterField(
            model_name="article",
            name="status",
            field=models.CharField(
                default=_STATUS_DRAFT,
                help_text="sysCodeManager 부모 SYS26209B020 하위 sysCodeSid (예: SYS26209B021~025)",
                max_length=50,
                verbose_name="발행 상태 (sysCodeSid)",
            ),
        ),
    ]
