from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_messages", "0005_messagesenderemail"),
    ]

    operations = [
        migrations.AddField(
            model_name="kakaotemplate",
            name="emtitle",
            field=models.CharField(
                blank=True,
                default="",
                max_length=500,
                help_text="알리고 알림톡 강조표기형 타이틀(emtitle_n)",
            ),
        ),
    ]
