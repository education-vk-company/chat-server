from .models import Attachment, Message


def serialize_attachment(attachment: Attachment) -> dict:
    return {
        "url": attachment.file.url if attachment.file else None,
        "thumbnail_url": attachment.thumbnail.url if attachment.thumbnail else None,
        "mime_type": attachment.mime_type,
        "size_bytes": attachment.size_bytes,
        "duration_seconds": attachment.duration_seconds,
        "width": attachment.width,
        "height": attachment.height,
        "status": attachment.status,
    }


def serialize_message(message: Message) -> dict:
    data = {
        "id": message.id,
        "chat_id": message.chat_id,
        "sender_id": message.sender_id,
        "type": message.type,
        "text": message.text if not message.is_deleted else "",
        "reply_to_id": message.reply_to_id,
        "is_deleted": message.is_deleted,
        "created_at": message.created_at.isoformat(),
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "attachment": None,
    }
    attachment = getattr(message, "attachment", None)
    if attachment is not None:
        data["attachment"] = serialize_attachment(attachment)
    return data
