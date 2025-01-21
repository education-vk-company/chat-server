from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX, make_password
from django.db import migrations

from apps.users.models import DELETED_USER_USERNAME


def create_deleted_user_placeholder(apps, schema_editor):
    User = apps.get_model("users", "User")
    user, _ = User.objects.get_or_create(
        username=DELETED_USER_USERNAME,
        defaults={
            "first_name": "",
            "last_name": "",
            "is_active": False,
            "password": make_password(None),
        },
    )
    changed = []
    if user.is_active:
        user.is_active = False
        changed.append("is_active")
    if not user.password.startswith(UNUSABLE_PASSWORD_PREFIX):
        user.password = make_password(None)
        changed.append("password")
    if changed:
        user.save(update_fields=changed)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_user_last_seen_at"),
    ]

    operations = [
        migrations.RunPython(create_deleted_user_placeholder, noop),
    ]
