import uuid


def attachment_upload_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"attachments/{uuid.uuid4()}.{ext}"


def attachment_thumbnail_path(instance, filename):
    return f"attachments/thumbnails/{uuid.uuid4()}.jpg"
