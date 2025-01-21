import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('chats', '0001_initial'),
        ('messaging', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='chat',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_chats', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='chatmember',
            name='chat',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_members', to='chats.chat'),
        ),
        migrations.AddField(
            model_name='chatmember',
            name='last_read_message',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='messaging.message'),
        ),
        migrations.AddField(
            model_name='chatmember',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_memberships', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='chat',
            name='members',
            field=models.ManyToManyField(related_name='chats', through='chats.ChatMember', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(
            model_name='chatmember',
            constraint=models.UniqueConstraint(fields=('chat', 'user'), name='unique_chat_member'),
        ),
    ]
