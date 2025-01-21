from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    avatar_url: str | None = None
    is_deleted: bool = False
    is_online: bool = False
    last_seen_at: str | None = None


class UpdateProfileRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
