from fastapi import APIRouter, Depends, File, Query, UploadFile

from ..deps import get_current_user
from ..schemas.users import UpdateProfileRequest, UserOut
from ..services import users as users_service

router = APIRouter()


@router.get("/me", response_model=UserOut)
async def get_me(current_user=Depends(get_current_user)):
    return users_service.serialize_user(current_user)


@router.patch("/me", response_model=UserOut)
async def update_me(body: UpdateProfileRequest, current_user=Depends(get_current_user)):
    return await users_service.update_profile(
        current_user.id, body.first_name, body.last_name, body.username
    )


@router.delete("/me", status_code=204)
async def delete_me(current_user=Depends(get_current_user)):
    await users_service.delete_account(current_user.id)


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    content = await file.read()
    return await users_service.set_avatar(current_user.id, file.filename, content)


@router.get("/search", response_model=list[UserOut])
async def search_users(q: str = Query(min_length=1), current_user=Depends(get_current_user)):
    return await users_service.search_users(q, current_user.id)
