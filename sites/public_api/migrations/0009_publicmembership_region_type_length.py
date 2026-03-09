# admin API에서 region_type에 sysCode 등 임의 값 허용 (max_length 확대, choices 제거)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_api', '0008_publicuseractivitylog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='publicmembership',
            name='region_type',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='지역 타입'),
        ),
    ]
