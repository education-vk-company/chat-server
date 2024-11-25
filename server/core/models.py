import uuid

from django.db import models


class UUIDModel(models.Model):
    id = models.UUIDField(editable=False, primary_key=True, default=uuid.uuid4)

    class Meta:
        abstract = True
