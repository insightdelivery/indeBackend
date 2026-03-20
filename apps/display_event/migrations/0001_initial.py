from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DisplayEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type_code", models.CharField(db_index=True, max_length=15)),
                ("content_type_code", models.CharField(db_index=True, max_length=15)),
                ("content_id", models.BigIntegerField(blank=True, null=True)),
                ("title", models.CharField(blank=True, max_length=255, null=True)),
                ("subtitle", models.CharField(blank=True, max_length=500, null=True)),
                ("image_url", models.CharField(blank=True, max_length=500, null=True)),
                ("link_url", models.CharField(blank=True, max_length=500, null=True)),
                ("display_order", models.IntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("start_at", models.DateTimeField(blank=True, null=True)),
                ("end_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "display_event",
                "ordering": ["-is_active", "display_order", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="displayevent",
            index=models.Index(fields=["event_type_code", "is_active", "display_order"], name="devent_evt_act_ord"),
        ),
        migrations.AddIndex(
            model_name="displayevent",
            index=models.Index(fields=["start_at", "end_at"], name="devent_start_end"),
        ),
    ]
