import logging
import time
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

_RETRY_DELAYS_SECONDS = (0.1, 0.3)


def _envelope(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"type": event_type, "data": data}


def _headers() -> dict[str, str]:
    return {"Authorization": f"apikey {settings.CENTRIFUGO_HTTP_API_KEY}"}


def _post_with_retry(path: str, payload: dict[str, Any], log_context: str) -> None:
    attempts = len(_RETRY_DELAYS_SECONDS) + 1
    for attempt in range(attempts):
        try:
            response = httpx.post(
                f"{settings.CENTRIFUGO_API_URL}/{path}",
                json=payload,
                headers=_headers(),
                timeout=5.0,
            )
            response.raise_for_status()
            return
        except httpx.HTTPError:
            if attempt < len(_RETRY_DELAYS_SECONDS):
                time.sleep(_RETRY_DELAYS_SECONDS[attempt])
            else:
                logger.exception("Failed to %s after %d attempts", log_context, attempts)


def publish(channel: str, event_type: str, data: dict[str, Any]) -> None:
    _post_with_retry(
        "publish",
        {"channel": channel, "data": _envelope(event_type, data)},
        f"publish {event_type} to Centrifugo channel {channel}",
    )


def broadcast(channels: list[str], event_type: str, data: dict[str, Any]) -> None:
    if not channels:
        return
    _post_with_retry(
        "broadcast",
        {"channels": channels, "data": _envelope(event_type, data)},
        f"broadcast {event_type} to Centrifugo channels {channels}",
    )
