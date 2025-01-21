from django.conf import settings
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from ..deps import get_current_user
from ..schemas.auth import ChangePasswordRequest, LoginRequest, LogoutRequest, RefreshRequest, TokenResponse
from ..services import auth as auth_service

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    username: str = Form(min_length=3, max_length=150),
    password: str = Form(min_length=8, max_length=128),
    first_name: str = Form(default=""),
    last_name: str = Form(default=""),
    avatar: UploadFile | None = File(default=None),
):
    avatar_filename = None
    avatar_content = None
    if avatar is not None and avatar.filename:
        avatar_content = await avatar.read()
        if len(avatar_content) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
        avatar_filename = avatar.filename
    return await auth_service.register(
        username, password, first_name, last_name, avatar_filename, avatar_content
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    return await auth_service.login(body.username, body.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    return await auth_service.refresh(body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest):
    await auth_service.logout(body.refresh_token)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(body: ChangePasswordRequest, current_user=Depends(get_current_user)):
    await auth_service.change_password(current_user.id, body.old_password, body.new_password)
