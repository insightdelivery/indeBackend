from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('public_api', '0006_publicmembership_is_staff'),
    ]

    operations = [
        migrations.CreateModel(
            name='Inquiry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('content', models.TextField()),
                ('answer', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('waiting', '접수'), ('answered', '답변완료')], default='waiting', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inquiries', to='public_api.publicmembership')),
            ],
            options={
                'verbose_name': '1:1 문의',
                'verbose_name_plural': '1:1 문의',
                'ordering': ['-created_at'],
            },
        ),
    ]
