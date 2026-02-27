from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faq', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='faq',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, blank=True, null=True),
        ),
    ]
