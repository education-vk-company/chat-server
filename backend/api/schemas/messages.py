from pydantic import BaseModel


class AttachmentOut(BaseModel):
    url: str | None = None
    thumbnail_url: str | None = None
    mime_type: str
    size_bytes: int
    duration_seconds: int | None = None
    width: int | None = None
    height: int | None = None
    status: str


class MessageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    type: str
    text: str
    reply_to_id: int | None = None
    is_deleted: bool
    created_at: str
    edited_at: str | None = None
    attachment: AttachmentOut | None = None


class SendMessageRequest(BaseModel):
    text: str
    reply_to_id: int | None = None


class EditMessageRequest(BaseModel):
    text: str


class MarkReadRequest(BaseModel):
    message_id: int
