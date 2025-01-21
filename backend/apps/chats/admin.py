from django.contrib import admin

from .models import Chat, ChatMember


class ChatMemberInline(admin.TabularInline):
    model = ChatMember
    extra = 0
    autocomplete_fields = ("user", "last_read_message")


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("id", "type", "title", "owner", "created_at")
    list_filter = ("type",)
    search_fields = ("title",)
    autocomplete_fields = ("owner",)
    inlines = [ChatMemberInline]


@admin.register(ChatMember)
class ChatMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "chat", "user", "role", "is_muted", "joined_at")
    list_filter = ("role", "is_muted")
    autocomplete_fields = ("chat", "user", "last_read_message")
