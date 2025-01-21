import uuid

from django.conf import settings
from django.db import models

VK_EDUCATION_BOT_USERNAME = "vk_education_bot"
VK_EDUCATION_CHAT_TITLE = "VK Education"


def chat_avatar_upload_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"chat_avatars/{uuid.uuid4()}.{ext}"


class Chat(models.Model):
    class Type(models.TextChoices):
        PRIVATE = "private", "Private"
        GROUP = "group", "Group"

    type = models.CharField(max_length=10, choices=Type.choices)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    avatar = models.ImageField(upload_to=chat_avatar_upload_path, null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_chats",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="ChatMember", related_name="chats"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chats"

    def __str__(self):
        return self.title or f"Chat #{self.pk}"


class ChatMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="chat_members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_memberships"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    is_muted = models.BooleanField(default=False)
    last_read_message = models.ForeignKey(
        "messaging.Message", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    cleared_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_members"
        constraints = [
            models.UniqueConstraint(fields=["chat", "user"], name="unique_chat_member"),
        ]

    def __str__(self):
        return f"{self.user_id} in chat {self.chat_id}"
