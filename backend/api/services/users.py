import uuid
from datetime import timedelta

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.chats.models import VK_EDUCATION_BOT_USERNAME, ChatMember
from apps.messaging.models import Message
from apps.users.models import DELETED_USER_USERNAME, User

from .base import db_call
from .chats import notify_chat_updated
from .serializers import serialize_user

AVATAR_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
LAST_SEEN_THROTTLE_SECONDS = 30


class UserError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code = code
        self.status = status
        super().__init__(code)


def save_avatar(user: User, filename: str, content: bytes) -> None:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in AVATAR_EXTENSIONS:
        raise UserError("invalid_file_type")
    user.avatar.save(f"{uuid.uuid4()}.{ext}", ContentFile(content), save=True)


@db_call
def get_user_by_id(user_id: int) -> User | None:
    return User.objects.filter(id=user_id, is_active=True).first()


@db_call
def search_users(query: str, exclude_user_id: int, limit: int = 20) -> list[dict]:
    users = (
        User.objects.filter(is_active=True)
        .filter(Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query))
        .exclude(id=exclude_user_id)
        .exclude(username=VK_EDUCATION_BOT_USERNAME)
        .exclude(username=DELETED_USER_USERNAME)
        .order_by("username")[:limit]
    )
    return [serialize_user(u) for u in users]


@db_call
def update_profile(
    user_id: int, first_name: str | None, last_name: str | None, username: str | None
) -> dict:
    user = User.objects.get(id=user_id)
    fields = []
    if first_name is not None:
        user.first_name = first_name
        fields.append("first_name")
    if last_name is not None:
        user.last_name = last_name
        fields.append("last_name")
    if username is not None and username != user.username:
        if User.objects.exclude(id=user_id).filter(username=username).exists():
            raise UserError("username_taken", status=409)
        user.username = username
        fields.append("username")
    if fields:
        try:
            user.save(update_fields=fields)
        except IntegrityError:
            raise UserError("username_taken", status=409)
    return serialize_user(user)


@db_call
def set_avatar(user_id: int, filename: str, content: bytes) -> dict:
    user = User.objects.get(id=user_id)
    save_avatar(user, filename, content)
    return serialize_user(user)


@db_call
def touch_last_seen(user_id: int) -> None:
    threshold = timezone.now() - timedelta(seconds=LAST_SEEN_THROTTLE_SECONDS)
    User.objects.filter(id=user_id).exclude(last_seen_at__gte=threshold).update(last_seen_at=timezone.now())


@db_call
def delete_account(user_id: int) -> None:
    try:
        placeholder = User.objects.get(username=DELETED_USER_USERNAME)
    except User.DoesNotExist:
        raise UserError("placeholder_missing", status=500)
    affected_chats = {}

    with transaction.atomic():
        Message.objects.filter(sender_id=user_id).update(sender_id=placeholder.id)

        for member in ChatMember.objects.filter(user_id=user_id).select_related("chat"):
            chat = member.chat
            affected_chats[chat.id] = chat
            if member.role == ChatMember.Role.OWNER:
                successor = chat.chat_members.exclude(user_id=user_id).order_by("joined_at").first()
                if successor is not None:
                    successor.role = ChatMember.Role.OWNER
                    successor.save(update_fields=["role"])
                    chat.owner_id = successor.user_id
                    chat.save(update_fields=["owner"])

            if ChatMember.objects.filter(chat_id=chat.id, user_id=placeholder.id).exists():
                member.delete()
            else:
                member.user_id = placeholder.id
                member.role = ChatMember.Role.MEMBER
                member.save(update_fields=["user", "role"])

        User.objects.filter(id=user_id).delete()

    for chat in affected_chats.values():
        notify_chat_updated(chat)

