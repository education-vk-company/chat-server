from pydantic import BaseModel

from .messages import MessageOut


class ChatMemberOut(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    avatar_url: str | None = None
    is_deleted: bool = False
    is_online: bool = False
    last_seen_at: str | None = None
    role: str


class ChatOut(BaseModel):
    id: int
    type: str
    title: str
    description: str
    avatar_url: str | None = None
    created_at: str
    updated_at: str
    my_role: str
    is_muted: bool
    unread_count: int
    last_message: MessageOut | None = None
    members: list[ChatMemberOut]


class DirectMessageOut(BaseModel):
    chat: ChatOut
    message: MessageOut


class UpdateChatSettingsRequest(BaseModel):
    title: str | None = None
    description: str | None = None


class AddMembersRequest(BaseModel):
    member_ids: list[int]


class UpdateMemberRoleRequest(BaseModel):
    role: str


class SetMuteRequest(BaseModel):
    is_muted: bool
