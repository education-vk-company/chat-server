import uuid
from datetime import datetime

from django.core.files.base import ContentFile
from django.db import connection, transaction
from django.utils import timezone

from apps.chats.models import VK_EDUCATION_BOT_USERNAME, Chat, ChatMember
from apps.messaging.models import Message
from apps.messaging.serializers import serialize_message
from apps.users.models import DELETED_USER_USERNAME, User
from realtime import Event, publish, user_channel

from .base import db_call
from .serializers import serialize_user

AVATAR_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}


class ChatError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code = code
        self.status = status
        super().__init__(code)


def _unread_count(chat_id: int, member: ChatMember) -> int:
    qs = Message.objects.filter(chat_id=chat_id, is_deleted=False).exclude(sender_id=member.user_id)
    if member.last_read_message_id:
        qs = qs.filter(id__gt=member.last_read_message_id)
    if member.cleared_at:
        qs = qs.filter(created_at__gt=member.cleared_at)
    return qs.count()


def _last_message(chat_id: int, after: datetime | None = None) -> Message | None:
    qs = Message.objects.filter(chat_id=chat_id, is_deleted=False)
    if after:
        qs = qs.filter(created_at__gt=after)
    return qs.order_by("-id").first()


def serialize_chat(chat: Chat, viewer: ChatMember) -> dict:
    last_message = _last_message(chat.id, viewer.cleared_at)
    return {
        "id": chat.id,
        "type": chat.type,
        "title": chat.title,
        "description": chat.description,
        "avatar_url": chat.avatar.url if chat.avatar else None,
        "created_at": chat.created_at.isoformat(),
        "updated_at": chat.updated_at.isoformat(),
        "my_role": viewer.role,
        "is_muted": viewer.is_muted,
        "unread_count": _unread_count(chat.id, viewer),
        "last_message": serialize_message(last_message) if last_message else None,
        "members": [
            {**serialize_user(m.user), "role": m.role}
            for m in chat.chat_members.select_related("user").all()
        ],
    }


def _notify_chat_created(chat: Chat, members: list[ChatMember]) -> None:
    for m in members:
        publish(user_channel(m.user_id), Event.CHAT_CREATED, {"chat": serialize_chat(chat, m)})


def notify_chat_updated(chat: Chat) -> None:
    for m in chat.chat_members.select_related("user").all():
        publish(user_channel(m.user_id), Event.CHAT_UPDATED, {"chat": serialize_chat(chat, m)})


def get_membership(chat_id: int, user_id: int) -> ChatMember:
    try:
        return ChatMember.objects.select_related("chat").get(chat_id=chat_id, user_id=user_id)
    except ChatMember.DoesNotExist:
        raise ChatError("not_found", status=404)


def _require_group_admin(member: ChatMember) -> None:
    if member.chat.type != Chat.Type.GROUP:
        raise ChatError("not_a_group")
    if member.role not in (ChatMember.Role.OWNER, ChatMember.Role.ADMIN):
        raise ChatError("forbidden", status=403)


def _avatar_ext(filename: str | None) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if filename and "." in filename else ""
    if ext not in AVATAR_EXTENSIONS:
        raise ChatError("invalid_file_type")
    return ext


def auto_join_vk_education(user: User) -> None:
    chat = (
        Chat.objects.filter(type=Chat.Type.GROUP, owner__username=VK_EDUCATION_BOT_USERNAME)
        .exclude(chat_members__user=user)
        .first()
    )
    if chat is None:
        return
    member = ChatMember.objects.create(chat=chat, user=user, role=ChatMember.Role.MEMBER)
    chat.updated_at = timezone.now()
    chat.save(update_fields=["updated_at"])

    name = user.first_name or user.username
    join_message = Message.objects.create(
        chat=chat, sender_id=chat.owner_id, type=Message.Type.TEXT, text=f"{name} присоединился к чату"
    )

    def _notify():
        _notify_chat_created(chat, [member])
        payload = serialize_message(join_message)
        for uid in chat.chat_members.values_list("user_id", flat=True):
            publish(user_channel(uid), Event.MESSAGE_NEW, {"message": payload})

    transaction.on_commit(_notify)


@db_call
def list_chats(user_id: int) -> list[dict]:
    memberships = (
        ChatMember.objects.filter(user_id=user_id)
        .select_related("chat")
        .order_by("-chat__updated_at")
    )
    return [serialize_chat(m.chat, m) for m in memberships]


@db_call
def get_chat(user_id: int, chat_id: int) -> dict:
    member = get_membership(chat_id, user_id)
    return serialize_chat(member.chat, member)


def _validate_private_target(user_id: int, other_user_id: int) -> None:
    if user_id == other_user_id:
        raise ChatError("cannot_chat_with_self")
    exists = (
        User.objects.filter(id=other_user_id, is_active=True)
        .exclude(username=VK_EDUCATION_BOT_USERNAME)
        .exclude(username=DELETED_USER_USERNAME)
        .exists()
    )
    if not exists:
        raise ChatError("user_not_found", status=404)


def get_or_create_private_chat(
    user_id: int, other_user_id: int
) -> tuple[Chat, ChatMember, ChatMember, bool]:
    _validate_private_target(user_id, other_user_id)

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(%s, %s)",
                [min(user_id, other_user_id), max(user_id, other_user_id)],
            )

        existing = (
            Chat.objects.filter(type=Chat.Type.PRIVATE)
            .filter(members__id=user_id)
            .filter(members__id=other_user_id)
            .first()
        )
        if existing is not None:
            my_member = ChatMember.objects.get(chat=existing, user_id=user_id)
            other_member = ChatMember.objects.get(chat=existing, user_id=other_user_id)
            return existing, my_member, other_member, False

        chat = Chat.objects.create(type=Chat.Type.PRIVATE)
        my_member, other_member = ChatMember.objects.bulk_create(
            [
                ChatMember(chat=chat, user_id=user_id, role=ChatMember.Role.MEMBER),
                ChatMember(chat=chat, user_id=other_user_id, role=ChatMember.Role.MEMBER),
            ]
        )
        return chat, my_member, other_member, True


@db_call
def create_group_chat(
    owner_id: int,
    title: str,
    member_ids: list[int],
    description: str = "",
    avatar_filename: str | None = None,
    avatar_content: bytes | None = None,
) -> dict:
    member_ids = {mid for mid in member_ids if mid != owner_id}
    valid_ids = set(User.objects.filter(id__in=member_ids, is_active=True).values_list("id", flat=True))
    if len(valid_ids) != len(member_ids):
        raise ChatError("user_not_found", status=404)

    with transaction.atomic():
        chat = Chat.objects.create(
            type=Chat.Type.GROUP, title=title, description=description, owner_id=owner_id
        )
        if avatar_content:
            ext = _avatar_ext(avatar_filename)
            chat.avatar.save(f"{uuid.uuid4()}.{ext}", ContentFile(avatar_content), save=True)
        rows = [ChatMember(chat=chat, user_id=owner_id, role=ChatMember.Role.OWNER)]
        rows += [ChatMember(chat=chat, user_id=uid, role=ChatMember.Role.MEMBER) for uid in valid_ids]
        members = ChatMember.objects.bulk_create(rows)

    _notify_chat_created(chat, members)
    owner_member = next(m for m in members if m.user_id == owner_id)
    return serialize_chat(chat, owner_member)


@db_call
def update_chat_settings(user_id: int, chat_id: int, title: str | None, description: str | None) -> dict:
    member = get_membership(chat_id, user_id)
    _require_group_admin(member)
    chat = member.chat
    fields = []
    if title is not None:
        chat.title = title
        fields.append("title")
    if description is not None:
        chat.description = description
        fields.append("description")
    if fields:
        chat.updated_at = timezone.now()
        chat.save(update_fields=[*fields, "updated_at"])
    notify_chat_updated(chat)
    return serialize_chat(chat, member)


@db_call
def set_chat_avatar(user_id: int, chat_id: int, filename: str, content: bytes) -> dict:
    member = get_membership(chat_id, user_id)
    _require_group_admin(member)
    chat = member.chat
    ext = _avatar_ext(filename)
    chat.avatar.save(f"{uuid.uuid4()}.{ext}", ContentFile(content), save=True)
    notify_chat_updated(chat)
    return serialize_chat(chat, member)


@db_call
def add_members(user_id: int, chat_id: int, member_ids: list[int]) -> dict:
    member = get_membership(chat_id, user_id)
    _require_group_admin(member)
    chat = member.chat

    existing_ids = set(chat.chat_members.values_list("user_id", flat=True))
    new_ids = [uid for uid in member_ids if uid not in existing_ids]
    valid_ids = set(User.objects.filter(id__in=new_ids, is_active=True).values_list("id", flat=True))
    if len(valid_ids) != len(new_ids):
        raise ChatError("user_not_found", status=404)

    with transaction.atomic():
        new_members = ChatMember.objects.bulk_create(
            [ChatMember(chat=chat, user_id=uid, role=ChatMember.Role.MEMBER) for uid in valid_ids]
        )
        chat.updated_at = timezone.now()
        chat.save(update_fields=["updated_at"])

    _notify_chat_created(chat, new_members)
    notify_chat_updated(chat)
    return serialize_chat(chat, member)


@db_call
def remove_member(user_id: int, chat_id: int, target_user_id: int) -> None:
    member = get_membership(chat_id, user_id)
    if member.chat.type != Chat.Type.GROUP:
        raise ChatError("not_a_group")
    if target_user_id != user_id:
        _require_group_admin(member)

    chat = member.chat
    try:
        target = ChatMember.objects.get(chat=chat, user_id=target_user_id)
    except ChatMember.DoesNotExist:
        raise ChatError("not_found", status=404)

    with transaction.atomic():
        target_role = target.role
        target.delete()
        chat_deleted = not chat.chat_members.exists()
        if chat_deleted:
            chat.delete()
        elif target_role == ChatMember.Role.OWNER:
            successor = chat.chat_members.order_by("joined_at").first()
            successor.role = ChatMember.Role.OWNER
            successor.save(update_fields=["role"])
            chat.owner_id = successor.user_id
            chat.save(update_fields=["owner"])

    publish(user_channel(target_user_id), Event.CHAT_MEMBER_REMOVED, {"chat_id": chat.id})
    if not chat_deleted:
        notify_chat_updated(chat)


@db_call
def update_member_role(user_id: int, chat_id: int, target_user_id: int, role: str) -> dict:
    member = get_membership(chat_id, user_id)
    if member.role != ChatMember.Role.OWNER:
        raise ChatError("forbidden", status=403)
    if role not in (ChatMember.Role.ADMIN, ChatMember.Role.MEMBER):
        raise ChatError("invalid_role")

    target = ChatMember.objects.filter(chat_id=chat_id, user_id=target_user_id).first()
    if target is None:
        raise ChatError("not_found", status=404)
    target.role = role
    target.save(update_fields=["role"])
    notify_chat_updated(member.chat)
    return serialize_chat(member.chat, member)


@db_call
def set_mute(user_id: int, chat_id: int, is_muted: bool) -> dict:
    member = get_membership(chat_id, user_id)
    member.is_muted = is_muted
    member.save(update_fields=["is_muted"])
    return serialize_chat(member.chat, member)


@db_call
def delete_chat(user_id: int, chat_id: int) -> None:
    member = get_membership(chat_id, user_id)
    chat = member.chat

    if chat.type == Chat.Type.GROUP:
        if member.role != ChatMember.Role.OWNER:
            raise ChatError("forbidden", status=403)
        member_ids = list(chat.chat_members.values_list("user_id", flat=True))
        chat.delete()
        for uid in member_ids:
            publish(user_channel(uid), Event.CHAT_MEMBER_REMOVED, {"chat_id": chat_id})
    else:
        member.cleared_at = timezone.now()
        member.save(update_fields=["cleared_at"])
