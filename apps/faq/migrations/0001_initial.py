from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='FAQ',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=255)),
                ('answer', models.TextField()),
                ('order', models.IntegerField(default=0)),
            ],
            options={
                'verbose_name': '자주 묻는 질문',
                'verbose_name_plural': '자주 묻는 질문',
                'ordering': ['order'],
            },
        ),
    ]
