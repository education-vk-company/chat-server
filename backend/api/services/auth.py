import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.users.models import RefreshToken, User

from ..security import create_access_token
from .base import db_call
from .chats import auto_join_vk_education
from .serializers import serialize_user
from .users import save_avatar


class AuthError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code = code
        self.status = status
        super().__init__(code)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _issue_refresh_token(user: User) -> str:
    raw_token = secrets.token_urlsafe(48)
    RefreshToken.objects.create(
        user=user,
        token_hash=_hash_token(raw_token),
        expires_at=timezone.now() + timedelta(seconds=settings.JWT_REFRESH_TTL_SECONDS),
    )
    return raw_token


def _tokens_for(user: User) -> dict:
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": _issue_refresh_token(user),
        "token_type": "bearer",
        "user": serialize_user(user),
    }


@db_call
def register(
    username: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    avatar_filename: str | None = None,
    avatar_content: bytes | None = None,
) -> dict:
    try:
        validate_password(password)
    except ValidationError:
        raise AuthError("weak_password")

    try:
        with transaction.atomic():
            if User.objects.filter(username=username).exists():
                raise AuthError("username_taken", status=409)
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            user.set_password(password)
            user.save(update_fields=["password"])
            if avatar_content:
                save_avatar(user, avatar_filename or "avatar.jpg", avatar_content)
            auto_join_vk_education(user)
    except IntegrityError:
        raise AuthError("username_taken", status=409)
    return _tokens_for(user)


@db_call
def login(username: str, password: str) -> dict:
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise AuthError("invalid_credentials", status=401)
    if not user.is_active or not user.check_password(password):
        raise AuthError("invalid_credentials", status=401)
    return _tokens_for(user)


@db_call
def refresh(raw_token: str) -> dict:
    token_hash = _hash_token(raw_token)
    with transaction.atomic():
        try:
            token = (
                RefreshToken.objects.select_related("user")
                .select_for_update()
                .get(token_hash=token_hash)
            )
        except RefreshToken.DoesNotExist:
            raise AuthError("invalid_refresh_token", status=401)
        if not token.is_active:
            raise AuthError("invalid_refresh_token", status=401)
        token.revoked_at = timezone.now()
        token.save(update_fields=["revoked_at"])
        result = _tokens_for(token.user)
    return result


@db_call
def change_password(user_id: int, old_password: str, new_password: str) -> None:
    user = User.objects.get(id=user_id)
    if not user.check_password(old_password):
        raise AuthError("invalid_credentials", status=401)
    try:
        validate_password(new_password, user=user)
    except ValidationError:
        raise AuthError("weak_password")
    user.set_password(new_password)
    user.save(update_fields=["password"])
    RefreshToken.objects.filter(user_id=user_id, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )


@db_call
def logout(raw_token: str) -> None:
    token_hash = _hash_token(raw_token)
    RefreshToken.objects.filter(token_hash=token_hash, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )

