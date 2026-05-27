import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, BigInteger,
    UniqueConstraint, Index, CheckConstraint,
)
from sqlalchemy.orm import relationship
from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    microsoft_id = Column(String(64), unique=True, nullable=True)
    email = Column(String(255))
    display_name = Column(String(128), nullable=False)
    minecraft_uuid = Column(String(36), unique=True, nullable=True)
    minecraft_username = Column(String(64), nullable=True)
    owns_java_edition = Column(Boolean, nullable=False, default=False)
    skin_model = Column(String(8), nullable=True)
    role = Column(String(16), nullable=False, default="user")
    is_banned = Column(Boolean, nullable=False, default=False)
    microsoft_refresh_token = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    seeds = relationship("Seed", back_populates="uploader", foreign_keys="Seed.uploader_id")
    comments = relationship("Comment", back_populates="author")
    likes = relationship("Like", back_populates="user")
    collections = relationship("Collection", back_populates="user")

    __table_args__ = (
        Index("idx_users_microsoft_id", "microsoft_id"),
        Index("idx_users_minecraft_uuid", "minecraft_uuid"),
    )


class Seed(Base):
    __tablename__ = "seeds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(50), nullable=False)
    description = Column(String(500), nullable=False)
    seed_value = Column(String(64), nullable=False)
    seed_numeric = Column(BigInteger, nullable=True)
    edition = Column(String(16), nullable=False)
    tested_version = Column(String(16), nullable=False)
    compatible_range = Column(String(32), nullable=True)
    world_type = Column(String(16), nullable=False, default="normal")
    mod_env = Column(String(16), nullable=False, default="vanilla")
    modpack_name = Column(String(128), nullable=True)
    modpack_version = Column(String(32), nullable=True)
    spawn_x = Column(Integer, nullable=False)
    spawn_z = Column(Integer, nullable=False)
    status = Column(String(16), nullable=False, default="pending")
    rejection_reason = Column(String(500), nullable=True)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    view_count = Column(Integer, nullable=False, default=0)
    like_count = Column(Integer, nullable=False, default=0)
    collection_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    uploader = relationship("User", back_populates="seeds", foreign_keys=[uploader_id])
    screenshots = relationship("Screenshot", back_populates="seed")
    key_coords = relationship("KeyCoord", back_populates="seed")
    tags = relationship("SeedTag", back_populates="seed")
    comments = relationship("Comment", back_populates="seed")
    likes = relationship("Like", back_populates="seed")

    __table_args__ = (
        Index("idx_seeds_status", "status"),
        Index("idx_seeds_edition_version", "edition", "tested_version"),
        Index("idx_seeds_uploader", "uploader_id"),
        Index("idx_seeds_created", "created_at"),
        Index("idx_seeds_likes", "like_count"),
        Index("idx_seeds_collections", "collection_count"),
        CheckConstraint(
            "edition IN ('java', 'bedrock')", name="ck_seeds_edition"
        ),
        CheckConstraint(
            "world_type IN ('normal', 'large_biomes', 'superflat')",
            name="ck_seeds_world_type",
        ),
        CheckConstraint(
            "mod_env IN ('vanilla', 'modpack', 'neoforge')", name="ck_seeds_mod_env"
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_seeds_status"
        ),
    )


class Screenshot(Base):
    __tablename__ = "screenshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seed_id = Column(Integer, ForeignKey("seeds.id", ondelete="CASCADE"), nullable=True)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String(512), nullable=False)
    is_cover = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    status = Column(String(16), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    seed = relationship("Seed", back_populates="screenshots")

    __table_args__ = (
        Index("idx_screenshots_seed", "seed_id"),
        Index("idx_screenshots_uploader", "uploader_id"),
        CheckConstraint(
            "status IN ('pending', 'active', 'orphaned')", name="ck_screenshots_status"
        ),
    )


class KeyCoord(Base):
    __tablename__ = "key_coords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seed_id = Column(Integer, ForeignKey("seeds.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(30), nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=True)
    z = Column(Integer, nullable=False)

    seed = relationship("Seed", back_populates="key_coords")

    __table_args__ = (Index("idx_key_coords_seed", "seed_id"),)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(32), unique=True, nullable=False)
    label = Column(String(32), nullable=False)
    icon = Column(String(8), nullable=True)
    category = Column(String(16), nullable=False)

    seeds = relationship("SeedTag", back_populates="tag")

    __table_args__ = (
        CheckConstraint(
            "category IN ('gameplay', 'feature', 'special')", name="ck_tags_category"
        ),
    )


class SeedTag(Base):
    __tablename__ = "seed_tags"

    seed_id = Column(Integer, ForeignKey("seeds.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    seed = relationship("Seed", back_populates="tags")
    tag = relationship("Tag", back_populates="seeds")


class Like(Base):
    __tablename__ = "likes"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    seed_id = Column(Integer, ForeignKey("seeds.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="likes")
    seed = relationship("Seed", back_populates="likes")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seed_id = Column(Integer, ForeignKey("seeds.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(String(1000), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    seed = relationship("Seed", back_populates="comments")
    author = relationship("User", back_populates="comments")

    __table_args__ = (Index("idx_comments_seed", "seed_id", "created_at"),)


class Version(Base):
    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    edition = Column(String(16), nullable=False)
    version = Column(String(16), nullable=False)
    is_latest = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("edition", "version"),)


class SeedView(Base):
    __tablename__ = "seed_views"

    seed_id = Column(Integer, ForeignKey("seeds.id", ondelete="CASCADE"), primary_key=True)
    session_key = Column(String(64), primary_key=True)
    viewed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_seed_views_lookup", "seed_id", "session_key", "viewed_at"),
    )


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)
    cover_strategy = Column(String(16), nullable=False, default="last")
    cover_seed_id = Column(Integer, ForeignKey("seeds.id", ondelete="SET NULL"), nullable=True)
    is_public = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="collections")
    seeds = relationship("CollectionSeed", back_populates="collection")

    __table_args__ = (
        Index("idx_collections_user", "user_id", "sort_order"),
        CheckConstraint(
            "cover_strategy IN ('first', 'last', 'manual')",
            name="ck_collections_cover_strategy",
        ),
    )


class CollectionSeed(Base):
    __tablename__ = "collection_seeds"

    collection_id = Column(
        Integer, ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    seed_id = Column(
        Integer, ForeignKey("seeds.id", ondelete="CASCADE"), primary_key=True
    )
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    collection = relationship("Collection", back_populates="seeds")

    __table_args__ = (
        Index("idx_collection_seeds_coll", "collection_id", "added_at"),
        Index("idx_collection_seeds_seed", "seed_id"),
    )


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seed_id = Column(Integer, ForeignKey("seeds.id", ondelete="CASCADE"), nullable=False)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reporter_ip_hash = Column(String(64), nullable=True)
    reason = Column(String(32), nullable=False)
    detail = Column(String(500), nullable=True)
    status = Column(String(16), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "reason IN ('screenshot_mismatch', 'wrong_version', 'duplicate', 'inappropriate', 'other')",
            name="ck_reports_reason",
        ),
        CheckConstraint(
            "status IN ('pending', 'reviewed', 'dismissed')", name="ck_reports_status"
        ),
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(32), nullable=False)
    message = Column(String(255), nullable=False)
    detail = Column(String(500), nullable=True)
    seed_id = Column(Integer, ForeignKey("seeds.id", ondelete="SET NULL"), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_notifications_user", "user_id", "is_read", "created_at"),
        CheckConstraint(
            "type IN ('seed_approved', 'seed_rejected')", name="ck_notifications_type"
        ),
    )
