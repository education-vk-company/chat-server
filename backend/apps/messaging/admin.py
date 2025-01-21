from django.contrib import admin

from .models import Attachment, Message


class AttachmentInline(admin.StackedInline):
    model = Attachment
    extra = 0


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "chat", "sender", "type", "is_deleted", "created_at")
    list_filter = ("type", "is_deleted")
    search_fields = ("text", "sender__username")
    autocomplete_fields = ("chat", "sender", "reply_to")
    inlines = [AttachmentInline]


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "status", "mime_type", "size_bytes", "duration_seconds")
    list_filter = ("status",)
    autocomplete_fields = ("message",)
