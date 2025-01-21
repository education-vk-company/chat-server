import time

import jwt
from django.conf import settings


def issue_connection_token(user_id: int) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + settings.CENTRIFUGO_TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, settings.CENTRIFUGO_CLIENT_TOKEN_HMAC_SECRET_KEY, algorithm="HS256")
