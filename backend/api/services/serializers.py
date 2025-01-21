from datetime import timedelta

from django.utils import timezone

from apps.users.models import User

ONLINE_THRESHOLD_SECONDS = 60


def serialize_user(user: User) -> dict:
    is_online = bool(
        user.last_seen_at
        and user.last_seen_at >= timezone.now() - timedelta(seconds=ONLINE_THRESHOLD_SECONDS)
    )
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "avatar_url": user.avatar.url if user.avatar else None,
        "is_deleted": not user.is_active,
        "is_online": is_online,
        "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
    }
