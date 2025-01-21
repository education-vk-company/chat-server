from django.conf import settings
from fastapi import APIRouter, Depends

from realtime import issue_connection_token, user_channel

from ..deps import get_current_user

router = APIRouter()


@router.get("/token")
async def get_realtime_token(current_user=Depends(get_current_user)):
    return {
        "token": issue_connection_token(current_user.id),
        "channel": user_channel(current_user.id),
        "expires_in": settings.CENTRIFUGO_TOKEN_TTL_SECONDS,
    }
