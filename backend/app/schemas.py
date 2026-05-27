from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator


# ── Tag ──

class TagBrief(BaseModel):
    key: str
    label: str
    icon: Optional[str] = None

    model_config = {"from_attributes": True}


# ── User ──

class UserBrief(BaseModel):
    id: int
    display_name: str
    minecraft_username: Optional[str] = None
    avatar_url: Optional[str] = None
    owns_java_edition: bool = False

    model_config = {"from_attributes": True}


class UserProfile(BaseModel):
    id: int
    display_name: str
    minecraft_username: Optional[str] = None
    avatar_url: Optional[str] = None
    owns_java_edition: bool = False
    approved_seed_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Screenshot ──

class ScreenshotOut(BaseModel):
    id: int
    url: str
    is_cover: bool
    sort_order: int

    model_config = {"from_attributes": True}


# ── KeyCoord ──

class KeyCoordInput(BaseModel):
    label: str = Field(min_length=1, max_length=30)
    x: int
    y: Optional[int] = None
    z: int


class KeyCoordOut(BaseModel):
    id: int
    label: str
    x: int
    y: Optional[int] = None
    z: int

    model_config = {"from_attributes": True}


# ── Seed ──

class SeedListItem(BaseModel):
    id: int
    title: str
    description_preview: str
    cover_url: Optional[str] = None
    seed_value: str
    edition: str
    tested_version: str
    tags: list[TagBrief] = []
    like_count: int = 0
    collection_count: int = 0
    view_count: int = 0
    is_liked: bool = False
    uploader: Optional[UserBrief] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SeedDetail(BaseModel):
    id: int
    title: str
    description: str
    seed_value: str
    edition: str
    tested_version: str
    compatible_range: Optional[str] = None
    world_type: str
    mod_env: str
    modpack_name: Optional[str] = None
    modpack_version: Optional[str] = None
    spawn_x: int
    spawn_z: int
    status: str
    screenshots: list[ScreenshotOut] = []
    key_coords: list[KeyCoordOut] = []
    tags: list[TagBrief] = []
    like_count: int = 0
    collection_count: int = 0
    view_count: int = 0
    is_liked: bool = False
    uploader: Optional[UserBrief] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SeedCreate(BaseModel):
    seed_value: str = Field(min_length=1, max_length=64)
    edition: str = Field(pattern="^(java|bedrock)$")
    tested_version: str = Field(min_length=1, max_length=16)
    compatible_range: Optional[str] = Field(default=None, max_length=32)
    world_type: str = Field(pattern="^(normal|large_biomes|superflat)$")
    mod_env: str = Field(pattern="^(vanilla|modpack|neoforge)$")
    modpack_name: Optional[str] = Field(default=None, max_length=128)
    modpack_version: Optional[str] = Field(default=None, max_length=32)
    spawn_x: int
    spawn_z: int
    title: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=500)
    tags: list[str] = Field(min_length=1)
    key_coords: list[KeyCoordInput] = []
    screenshot_ids: list[int] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def check_modpack(self):
        if self.mod_env == "modpack" and not self.modpack_name:
            raise ValueError("modpack_name is required when mod_env is 'modpack'")
        return self


# ── Comment ──

class CommentInput(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class CommentOut(BaseModel):
    id: int
    content: str
    author: Optional[UserBrief] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Collection ──

class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=200)
    is_public: bool = False


class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=200)
    cover_strategy: Optional[str] = Field(default=None, pattern="^(first|last|manual)$")
    cover_seed_id: Optional[int] = None
    is_public: Optional[bool] = None
    sort_order: Optional[int] = None


class CollectionSummary(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    cover_url: Optional[str] = None
    seed_count: int = 0
    is_public: bool = False
    sort_order: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CollectionDetail(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    cover_strategy: str
    cover_seed_id: Optional[int] = None
    cover_url: Optional[str] = None
    is_public: bool = False
    owner: Optional[UserBrief] = None
    seeds: list[SeedListItem] = []
    meta: Optional["PaginationMeta"] = None

    model_config = {"from_attributes": True}


# ── Report ──

class ReportCreate(BaseModel):
    reason: str = Field(pattern="^(screenshot_mismatch|wrong_version|duplicate|inappropriate|other)$")
    detail: Optional[str] = Field(default=None, max_length=500)


# ── Version ──

class VersionOut(BaseModel):
    id: int
    edition: str
    version: str
    is_latest: bool
    sort_order: int

    model_config = {"from_attributes": True}


class VersionCreate(BaseModel):
    edition: str = Field(pattern="^(java|bedrock)$")
    version: str = Field(min_length=1, max_length=16)
    is_latest: bool = False


# ── Notification ──

class NotificationOut(BaseModel):
    id: int
    type: str
    message: str
    detail: Optional[str] = None
    seed_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Pagination ──

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int


# ── Response Envelope ──

class Envelope(BaseModel):
    data: object
    meta: Optional[PaginationMeta] = None


class ErrorResponse(BaseModel):
    error: dict


# ── Auth ──

class AuthMeResponse(BaseModel):
    id: int
    display_name: str
    minecraft_uuid: Optional[str] = None
    minecraft_username: Optional[str] = None
    owns_java_edition: bool = False
    avatar_url: Optional[str] = None
    role: str
    unread_count: int = 0
    created_at: datetime
