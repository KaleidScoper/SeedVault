import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import User, Notification


def create_jwt(user_id: int, role: str) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": now + timedelta(seconds=settings.JWT_EXPIRE_SECONDS),
        "iat": now,
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_jwt(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return None


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_microsoft_id(db: AsyncSession, ms_id: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.microsoft_id == ms_id))
    return result.scalar_one_or_none()


async def create_or_update_user(
    db: AsyncSession,
    microsoft_id: str,
    email: Optional[str],
    display_name: str,
    minecraft_uuid: Optional[str] = None,
    minecraft_username: Optional[str] = None,
    owns_java_edition: bool = False,
) -> User:
    user = await get_user_by_microsoft_id(db, microsoft_id)
    if user:
        user.email = email
        user.display_name = display_name
        user.last_login_at = datetime.utcnow()
        if minecraft_uuid:
            user.minecraft_uuid = minecraft_uuid
        if minecraft_username:
            user.minecraft_username = minecraft_username
        user.owns_java_edition = owns_java_edition
    else:
        # Check if MC UUID already bound to another user
        if minecraft_uuid:
            existing = await db.execute(
                select(User).where(User.minecraft_uuid == minecraft_uuid)
            )
            if existing.scalar_one_or_none():
                minecraft_uuid = None
                minecraft_username = None

        user = User(
            microsoft_id=microsoft_id,
            email=email,
            display_name=display_name,
            minecraft_uuid=minecraft_uuid,
            minecraft_username=minecraft_username,
            owns_java_edition=owns_java_edition,
            last_login_at=datetime.utcnow(),
        )
        db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def avatar_url(uuid: Optional[str], size: int = 80) -> Optional[str]:
    if not uuid:
        return None
    return f"https://mc-heads.net/avatar/{uuid}/{size}"


async def get_unread_count(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count()).where(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    return result.scalar() or 0


def hash_session_key(seed_id: int, ip: str, ua: str) -> str:
    raw = f"{seed_id}|{ip}|{ua}"
    return hmac.new(
        settings.SECRET_KEY.encode(), raw.encode(), hashlib.sha256
    ).hexdigest()
