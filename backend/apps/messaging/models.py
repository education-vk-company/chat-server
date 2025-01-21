from django.conf import settings
from django.db import models

from .storage import attachment_thumbnail_path, attachment_upload_path


class Message(models.Model):
    class Type(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        VOICE = "voice", "Voice"
        VIDEO_CIRCLE = "video_circle", "Video circle"
        FILE = "file", "File"

    chat = models.ForeignKey("chats.Chat", on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.TEXT)
    text = models.TextField(blank=True)
    reply_to = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replies"
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "messages"
        ordering = ["id"]
        indexes = [models.Index(fields=["chat", "id"])]

    def __str__(self):
        return f"Message #{self.pk} in chat {self.chat_id}"


class Attachment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name="attachment")
    file = models.FileField(upload_to=attachment_upload_path)
    thumbnail = models.ImageField(upload_to=attachment_thumbnail_path, null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    processing_error = models.TextField(blank=True)

    class Meta:
        db_table = "message_attachments"

    def __str__(self):
        return f"Attachment for message #{self.message_id}"
