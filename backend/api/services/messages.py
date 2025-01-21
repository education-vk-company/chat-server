import mimetypes
import uuid

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.chats.models import Chat, ChatMember
from apps.messaging.models import Attachment, Message
from apps.messaging.serializers import serialize_message
from apps.messaging.tasks import process_attachment
from apps.users.models import User
from realtime import Event, broadcast, user_channel

from .base import db_call
from .chats import ChatError, _notify_chat_created, get_membership, get_or_create_private_chat, serialize_chat
from .serializers import serialize_user

MEDIA_TYPES = {
    Message.Type.IMAGE,
    Message.Type.VIDEO,
    Message.Type.VOICE,
    Message.Type.VIDEO_CIRCLE,
    Message.Type.FILE,
}

MEDIA_EXTENSIONS = {
    Message.Type.IMAGE: {"jpg", "jpeg", "png", "webp", "gif"},
    Message.Type.VIDEO: {"mp4", "webm", "mov"},
    Message.Type.VOICE: {"ogg", "mp3", "m4a", "wav", "webm"},
    Message.Type.VIDEO_CIRCLE: {"mp4", "webm"},
    Message.Type.FILE: {
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "zip", "rar", "7z",
        "jpg", "jpeg", "png", "webp", "gif", "mp4", "webm", "mov", "mp3", "ogg", "wav", "m4a",
    },
}


def _member_channels(chat_id: int, exclude_user_id: int | None = None) -> list[str]:
    qs = ChatMember.objects.filter(chat_id=chat_id)
    if exclude_user_id is not None:
        qs = qs.exclude(user_id=exclude_user_id)
    return [user_channel(uid) for uid in qs.values_list("user_id", flat=True)]


def _touch_chat(chat_id: int) -> None:
    Chat.objects.filter(id=chat_id).update(updated_at=timezone.now())


def _check_reply_to(chat_id: int, reply_to_id: int | None) -> None:
    if reply_to_id is None:
        return
    if not Message.objects.filter(id=reply_to_id, chat_id=chat_id, is_deleted=False).exists():
        raise ChatError("reply_to_not_found", status=404)


@db_call
def list_messages(user_id: int, chat_id: int, before_id: int | None, limit: int = 30) -> list[dict]:
    member = get_membership(chat_id, user_id)
    qs = Message.objects.filter(chat_id=chat_id).select_related("attachment").order_by("-id")
    if member.cleared_at:
        qs = qs.filter(created_at__gt=member.cleared_at)
    if before_id is not None:
        qs = qs.filter(id__lt=before_id)
    messages = list(qs[: min(limit, 100)])
    messages.reverse()
    return [serialize_message(m) for m in messages]


@db_call
def send_text_message(user_id: int, chat_id: int, text: str, reply_to_id: int | None) -> dict:
    get_membership(chat_id, user_id)
    if not text.strip():
        raise ChatError("empty_message")
    _check_reply_to(chat_id, reply_to_id)

    with transaction.atomic():
        message = Message.objects.create(
            chat_id=chat_id,
            sender_id=user_id,
            type=Message.Type.TEXT,
            text=text,
            reply_to_id=reply_to_id,
        )
        _touch_chat(chat_id)

    payload = serialize_message(message)
    broadcast(_member_channels(chat_id), Event.MESSAGE_NEW, {"message": payload})
    return payload


@db_call
def send_media_message(
    user_id: int,
    chat_id: int,
    message_type: str,
    filename: str,
    content: bytes,
    mime_type: str | None,
    reply_to_id: int | None,
    text: str = "",
) -> dict:
    get_membership(chat_id, user_id)
    if message_type not in MEDIA_TYPES:
        raise ChatError("invalid_message_type")
    _check_reply_to(chat_id, reply_to_id)

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in MEDIA_EXTENSIONS[message_type]:
        raise ChatError("invalid_file_type")

    with transaction.atomic():
        message = Message.objects.create(
            chat_id=chat_id, sender_id=user_id, type=message_type, text=text, reply_to_id=reply_to_id
        )
        attachment = Attachment(
            message=message,
            mime_type=mime_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
            size_bytes=len(content),
        )
        attachment.file.save(f"{uuid.uuid4()}.{ext}", ContentFile(content), save=True)
        _touch_chat(chat_id)

    process_attachment.delay(attachment.id)

    payload = serialize_message(message)
    broadcast(_member_channels(chat_id), Event.MESSAGE_NEW, {"message": payload})
    return payload


@db_call
def send_direct_text_message(user_id: int, other_user_id: int, text: str, reply_to_id: int | None) -> dict:
    if not text.strip():
        raise ChatError("empty_message")

    with transaction.atomic():
        chat, my_member, other_member, created = get_or_create_private_chat(user_id, other_user_id)
        _check_reply_to(chat.id, reply_to_id)
        message = Message.objects.create(
            chat_id=chat.id, sender_id=user_id, type=Message.Type.TEXT, text=text, reply_to_id=reply_to_id
        )
        _touch_chat(chat.id)

    if created:
        _notify_chat_created(chat, [my_member, other_member])

    payload = serialize_message(message)
    broadcast(_member_channels(chat.id), Event.MESSAGE_NEW, {"message": payload})
    return {"chat": serialize_chat(chat, my_member), "message": payload}


@db_call
def send_direct_media_message(
    user_id: int,
    other_user_id: int,
    message_type: str,
    filename: str,
    content: bytes,
    mime_type: str | None,
    reply_to_id: int | None,
    text: str = "",
) -> dict:
    if message_type not in MEDIA_TYPES:
        raise ChatError("invalid_message_type")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in MEDIA_EXTENSIONS[message_type]:
        raise ChatError("invalid_file_type")

    with transaction.atomic():
        chat, my_member, other_member, created = get_or_create_private_chat(user_id, other_user_id)
        _check_reply_to(chat.id, reply_to_id)
        message = Message.objects.create(
            chat_id=chat.id, sender_id=user_id, type=message_type, text=text, reply_to_id=reply_to_id
        )
        attachment = Attachment(
            message=message,
            mime_type=mime_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
            size_bytes=len(content),
        )
        attachment.file.save(f"{uuid.uuid4()}.{ext}", ContentFile(content), save=True)
        _touch_chat(chat.id)

    process_attachment.delay(attachment.id)

    if created:
        _notify_chat_created(chat, [my_member, other_member])

    payload = serialize_message(message)
    broadcast(_member_channels(chat.id), Event.MESSAGE_NEW, {"message": payload})
    return {"chat": serialize_chat(chat, my_member), "message": payload}


@db_call
def edit_message(user_id: int, chat_id: int, message_id: int, text: str) -> dict:
    get_membership(chat_id, user_id)
    try:
        message = Message.objects.select_related("attachment").get(id=message_id, chat_id=chat_id)
    except Message.DoesNotExist:
        raise ChatError("not_found", status=404)
    if message.is_deleted:
        raise ChatError("not_found", status=404)
    if message.sender_id != user_id:
        raise ChatError("forbidden", status=403)
    if message.type == Message.Type.TEXT and not text.strip():
        raise ChatError("empty_message")

    message.text = text
    message.edited_at = timezone.now()
    message.save(update_fields=["text", "edited_at"])

    payload = serialize_message(message)
    broadcast(_member_channels(chat_id), Event.MESSAGE_UPDATED, {"message": payload})
    return payload


@db_call
def delete_message(user_id: int, chat_id: int, message_id: int) -> None:
    member = get_membership(chat_id, user_id)
    try:
        message = Message.objects.get(id=message_id, chat_id=chat_id)
    except Message.DoesNotExist:
        raise ChatError("not_found", status=404)

    is_privileged = member.role in (ChatMember.Role.OWNER, ChatMember.Role.ADMIN)
    if message.sender_id != user_id and not is_privileged:
        raise ChatError("forbidden", status=403)

    message.is_deleted = True
    message.deleted_at = timezone.now()
    message.text = ""
    message.save(update_fields=["is_deleted", "deleted_at", "text"])

    broadcast(
        _member_channels(chat_id), Event.MESSAGE_DELETED, {"chat_id": chat_id, "message_id": message_id}
    )


@db_call
def mark_read(user_id: int, chat_id: int, message_id: int) -> dict:
    member = get_membership(chat_id, user_id)
    try:
        message = Message.objects.get(id=message_id, chat_id=chat_id)
    except Message.DoesNotExist:
        raise ChatError("not_found", status=404)

    if member.last_read_message_id is None or message.id > member.last_read_message_id:
        member.last_read_message_id = message.id
        member.save(update_fields=["last_read_message"])

    broadcast(
        _member_channels(chat_id, exclude_user_id=user_id),
        Event.MESSAGE_READ,
        {"chat_id": chat_id, "user_id": user_id, "last_read_message_id": member.last_read_message_id},
    )
    return {"chat_id": chat_id, "last_read_message_id": member.last_read_message_id}


@db_call
def get_read_by(user_id: int, chat_id: int, message_id: int) -> list[dict]:
    get_membership(chat_id, user_id)
    try:
        message = Message.objects.get(id=message_id, chat_id=chat_id)
    except Message.DoesNotExist:
        raise ChatError("not_found", status=404)

    reader_ids = (
        ChatMember.objects.filter(chat_id=chat_id, last_read_message_id__gte=message_id)
        .exclude(user_id=message.sender_id)
        .values_list("user_id", flat=True)
    )
    readers = User.objects.filter(id__in=reader_ids)
    return [serialize_user(u) for u in readers]
