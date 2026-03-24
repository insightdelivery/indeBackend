from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("display_event", "0004_rename_devent_evt_act_ord_event_banne_event_t_f5f5a8_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="displayevent",
            name="badge_text",
            field=models.CharField(
                blank=True,
                db_comment="히어로 상단 배지 칩 문구. NULL/공백이면 노출 안 함",
                max_length=100,
                null=True,
            ),
        ),
    ]
