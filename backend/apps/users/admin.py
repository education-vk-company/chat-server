from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import RefreshToken, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Profile", {"fields": ("avatar",)}),)
    list_display = ("id", "username", "email", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "expires_at", "revoked_at")
    list_filter = ("revoked_at",)
    search_fields = ("user__username",)
    autocomplete_fields = ("user",)
