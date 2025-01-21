from django.conf import settings
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from ..deps import get_current_user
from ..schemas.chats import (
    AddMembersRequest,
    ChatOut,
    SetMuteRequest,
    UpdateChatSettingsRequest,
    UpdateMemberRoleRequest,
)
from ..services import chats as chats_service

router = APIRouter()


@router.get("", response_model=list[ChatOut])
async def list_chats(current_user=Depends(get_current_user)):
    return await chats_service.list_chats(current_user.id)


@router.post("/group", response_model=ChatOut, status_code=201)
async def create_group_chat(
    title: str = Form(...),
    description: str = Form(default=""),
    member_ids: list[int] = Form(default=[]),
    avatar: UploadFile | None = File(default=None),
    current_user=Depends(get_current_user),
):
    avatar_filename = None
    avatar_content = None
    if avatar is not None and avatar.filename:
        avatar_content = await avatar.read()
        if len(avatar_content) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
        avatar_filename = avatar.filename
    return await chats_service.create_group_chat(
        current_user.id, title, member_ids, description, avatar_filename, avatar_content
    )


@router.get("/{chat_id}", response_model=ChatOut)
async def get_chat(chat_id: int, current_user=Depends(get_current_user)):
    return await chats_service.get_chat(current_user.id, chat_id)


@router.patch("/{chat_id}", response_model=ChatOut)
async def update_chat_settings(
    chat_id: int, body: UpdateChatSettingsRequest, current_user=Depends(get_current_user)
):
    return await chats_service.update_chat_settings(current_user.id, chat_id, body.title, body.description)


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(chat_id: int, current_user=Depends(get_current_user)):
    await chats_service.delete_chat(current_user.id, chat_id)


@router.patch("/{chat_id}/mute", response_model=ChatOut)
async def set_mute(chat_id: int, body: SetMuteRequest, current_user=Depends(get_current_user)):
    return await chats_service.set_mute(current_user.id, chat_id, body.is_muted)


@router.post("/{chat_id}/avatar", response_model=ChatOut)
async def upload_chat_avatar(
    chat_id: int, file: UploadFile = File(...), current_user=Depends(get_current_user)
):
    content = await file.read()
    return await chats_service.set_chat_avatar(current_user.id, chat_id, file.filename, content)


@router.post("/{chat_id}/members", response_model=ChatOut, status_code=201)
async def add_members(chat_id: int, body: AddMembersRequest, current_user=Depends(get_current_user)):
    return await chats_service.add_members(current_user.id, chat_id, body.member_ids)


@router.delete("/{chat_id}/members/{user_id}", status_code=204)
async def remove_member(chat_id: int, user_id: int, current_user=Depends(get_current_user)):
    await chats_service.remove_member(current_user.id, chat_id, user_id)


@router.patch("/{chat_id}/members/{user_id}", response_model=ChatOut)
async def update_member_role(
    chat_id: int, user_id: int, body: UpdateMemberRoleRequest, current_user=Depends(get_current_user)
):
    return await chats_service.update_member_role(current_user.id, chat_id, user_id, body.role)
