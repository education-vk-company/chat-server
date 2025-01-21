from asgiref.sync import sync_to_async
from django.db import close_old_connections


def db_call(fn):
    def wrapped(*args, **kwargs):
        close_old_connections()
        try:
            return fn(*args, **kwargs)
        finally:
            close_old_connections()

    wrapped.__name__ = getattr(fn, "__name__", "wrapped")
    return sync_to_async(wrapped, thread_sensitive=False)
