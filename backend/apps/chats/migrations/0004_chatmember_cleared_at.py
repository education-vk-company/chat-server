from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chats", "0003_vk_education_bot"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmember",
            name="cleared_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
