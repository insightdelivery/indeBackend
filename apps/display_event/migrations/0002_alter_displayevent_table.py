from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("display_event", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="displayevent",
            table="event_banner",
        ),
    ]
