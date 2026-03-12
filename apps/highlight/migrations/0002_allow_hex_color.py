# color: choice 제거, 헥스값(#RRGGBB) 허용

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('highlight', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='articlehighlight',
            name='color',
            field=models.CharField(default='yellow', max_length=20, verbose_name='색상'),
        ),
    ]
