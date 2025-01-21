import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('messaging', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='sender',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='attachment',
            name='message',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='attachment', to='messaging.message'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['chat', 'id'], name='messages_chat_id_ae5eb5_idx'),
        ),
    ]
