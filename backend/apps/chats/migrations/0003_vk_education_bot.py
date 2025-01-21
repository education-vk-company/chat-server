from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX, make_password
from django.db import migrations

from apps.chats.models import VK_EDUCATION_BOT_USERNAME, VK_EDUCATION_CHAT_TITLE


def create_vk_education_bot(apps, schema_editor):
    User = apps.get_model("users", "User")
    Chat = apps.get_model("chats", "Chat")
    ChatMember = apps.get_model("chats", "ChatMember")

    bot, _ = User.objects.get_or_create(
        username=VK_EDUCATION_BOT_USERNAME,
        defaults={"first_name": "VK Education", "is_active": True, "password": make_password(None)},
    )
    if not bot.password.startswith(UNUSABLE_PASSWORD_PREFIX):
        bot.password = make_password(None)
        bot.save(update_fields=["password"])

    chat, created = Chat.objects.get_or_create(
        owner=bot,
        type="group",
        title=VK_EDUCATION_CHAT_TITLE,
    )
    if created:
        ChatMember.objects.create(chat=chat, user=bot, role="owner")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("chats", "0002_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_vk_education_bot, noop),
    ]
