import json
import logging
import subprocess
import tempfile
import uuid

from celery import shared_task
from django.core.files.base import ContentFile
from django.db import close_old_connections
from PIL import Image

from apps.chats.models import ChatMember
from realtime import Event, broadcast, user_channel

from .models import Attachment, Message
from .serializers import serialize_message

logger = logging.getLogger(__name__)


def _ffprobe(path: str) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        capture_output=True,
        text=True,
        timeout=60,
    )
    result.check_returncode()
    return json.loads(result.stdout)


def _extract_thumbnail_bytes(src_path: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
        subprocess.run(
            ["ffmpeg", "-y", "-i", src_path, "-ss", "00:00:00.500", "-vframes", "1", tmp.name],
            capture_output=True,
            timeout=60,
            check=True,
        )
        tmp.seek(0)
        return tmp.read()


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def process_attachment(self, attachment_id: int) -> None:
    close_old_connections()
    try:
        attachment = Attachment.objects.select_related("message").get(pk=attachment_id)
    except Attachment.DoesNotExist:
        return

    try:
        path = attachment.file.path
        message_type = attachment.message.type

        if message_type == Message.Type.IMAGE:
            with Image.open(path) as img:
                attachment.width, attachment.height = img.size

        elif message_type in (Message.Type.VIDEO, Message.Type.VOICE, Message.Type.VIDEO_CIRCLE):
            probe = _ffprobe(path)
            fmt = probe.get("format", {})
            attachment.duration_seconds = int(float(fmt.get("duration", 0) or 0))
            video_stream = next(
                (s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None
            )
            if video_stream:
                attachment.width = video_stream.get("width")
                attachment.height = video_stream.get("height")
                thumb_bytes = _extract_thumbnail_bytes(path)
                attachment.thumbnail.save(
                    f"{uuid.uuid4()}.jpg", ContentFile(thumb_bytes), save=False
                )

        attachment.status = Attachment.Status.READY
        attachment.processing_error = ""
    except Exception as exc:
        logger.exception("Failed to process attachment %s", attachment_id)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=self.default_retry_delay)
        attachment.status = Attachment.Status.FAILED
        attachment.processing_error = str(exc)[:1000]

    attachment.save()

    message = attachment.message
    member_ids = ChatMember.objects.filter(chat_id=message.chat_id).values_list(
        "user_id", flat=True
    )
    channels = [user_channel(uid) for uid in member_ids]
    broadcast(channels, Event.MESSAGE_UPDATED, {"message": serialize_message(message)})
