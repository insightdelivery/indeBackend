# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inquiry", "0002_inquiry_type_attachment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inquiry",
            name="inquiry_type",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
