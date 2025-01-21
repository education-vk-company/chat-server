from django.conf import settings
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from ..deps import get_current_user
from ..schemas.chats import DirectMessageOut
from ..schemas.messages import EditMessageRequest, MarkReadRequest, MessageOut, SendMessageRequest
from ..schemas.users import UserOut
from ..services import messages as messages_service

router = APIRouter()


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
async def list_messages(
    chat_id: int,
    before_id: int | None = Query(default=None),
    limit: int = Query(default=30, le=100, ge=1),
    current_user=Depends(get_current_user),
):
    return await messages_service.list_messages(current_user.id, chat_id, before_id, limit)


@router.post("/{chat_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(chat_id: int, body: SendMessageRequest, current_user=Depends(get_current_user)):
    return await messages_service.send_text_message(current_user.id, chat_id, body.text, body.reply_to_id)


@router.post(
    "/{chat_id}/messages/media", response_model=MessageOut, status_code=status.HTTP_201_CREATED
)
async def send_media_message(
    chat_id: int,
    type: str = Form(...),
    text: str = Form(default=""),
    reply_to_id: int | None = Form(default=None),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
    return await messages_service.send_media_message(
        current_user.id, chat_id, type, file.filename, content, file.content_type, reply_to_id, text
    )


@router.patch("/{chat_id}/messages/{message_id}", response_model=MessageOut)
async def edit_message(
    chat_id: int, message_id: int, body: EditMessageRequest, current_user=Depends(get_current_user)
):
    return await messages_service.edit_message(current_user.id, chat_id, message_id, body.text)


@router.delete("/{chat_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(chat_id: int, message_id: int, current_user=Depends(get_current_user)):
    await messages_service.delete_message(current_user.id, chat_id, message_id)


@router.post("/{chat_id}/read")
async def mark_read(chat_id: int, body: MarkReadRequest, current_user=Depends(get_current_user)):
    return await messages_service.mark_read(current_user.id, chat_id, body.message_id)


@router.get("/{chat_id}/messages/{message_id}/read-by", response_model=list[UserOut])
async def get_read_by(chat_id: int, message_id: int, current_user=Depends(get_current_user)):
    return await messages_service.get_read_by(current_user.id, chat_id, message_id)


@router.post("/direct/{other_user_id}", response_model=DirectMessageOut, status_code=status.HTTP_201_CREATED)
async def send_direct_message(
    other_user_id: int, body: SendMessageRequest, current_user=Depends(get_current_user)
):
    return await messages_service.send_direct_text_message(
        current_user.id, other_user_id, body.text, body.reply_to_id
    )


@router.post(
    "/direct/{other_user_id}/media", response_model=DirectMessageOut, status_code=status.HTTP_201_CREATED
)
async def send_direct_media_message(
    other_user_id: int,
    type: str = Form(...),
    text: str = Form(default=""),
    reply_to_id: int | None = Form(default=None),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
    return await messages_service.send_direct_media_message(
        current_user.id, other_user_id, type, file.filename, content, file.content_type, reply_to_id, text
    )
