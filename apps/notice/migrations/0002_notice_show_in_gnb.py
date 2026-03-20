from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notice", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notice",
            name="show_in_gnb",
            field=models.BooleanField(default=False, verbose_name="GNB 상단에 표시"),
        ),
    ]
