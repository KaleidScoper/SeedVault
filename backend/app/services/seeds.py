import math
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models import (
    Seed, Screenshot, KeyCoord, Tag, SeedTag, Like, User, SeedView,
    CollectionSeed,
)
from app.schemas import SeedCreate, KeyCoordInput
from app.services.auth import hash_session_key


def _build_hot_score_expr():
    """SQL expression for hot score: (likes*0.7 + views*0.3) / (hours_since_created + 4)^1.2"""
    hours_expr = (
        func.julianday("now") - func.julianday(Seed.created_at)
    ) * 24
    numerator = Seed.like_count * 0.7 + Seed.view_count * 0.3
    denominator = func.pow(hours_expr + 4, 1.2)
    return numerator / denominator


async def list_seeds(
    db: AsyncSession,
    edition: Optional[str] = None,
    version: Optional[str] = None,
    world_type: Optional[str] = None,
    tags: Optional[list[str]] = None,
    mod_env: Optional[str] = None,
    sort: str = "popular",
    q: Optional[str] = None,
    uploader_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 24,
    current_user_id: Optional[int] = None,
) -> tuple[list[dict], int]:
    # Base query
    conditions = [Seed.status == "approved"]

    if uploader_id:
        conditions.append(Seed.uploader_id == uploader_id)
    if edition:
        conditions.append(Seed.edition == edition)
    if version:
        if version.count(".") == 1:
            conditions.append(Seed.tested_version.like(f"{version}.%"))
        else:
            conditions.append(Seed.tested_version == version)
    if world_type:
        conditions.append(Seed.world_type == world_type)
    if mod_env:
        conditions.append(Seed.mod_env == mod_env)
    if q:
        conditions.append(
            or_(
                Seed.title.ilike(f"%{q}%"),
                Seed.description.ilike(f"%{q}%"),
            )
        )

    # Tag filtering (AND logic)
    if tags:
        for tag_key in tags:
            conditions.append(
                Seed.id.in_(
                    select(SeedTag.seed_id).join(Tag).where(Tag.key == tag_key)
                )
            )

    # Count query
    count_q = select(func.count()).select_from(Seed)
    if conditions:
        count_q = count_q.where(and_(*conditions))
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Data query with sorting
    data_q = select(Seed).options(
        selectinload(Seed.tags).joinedload(SeedTag.tag),
        selectinload(Seed.screenshots),
        selectinload(Seed.uploader),
    )

    if conditions:
        data_q = data_q.where(and_(*conditions))

    if sort == "newest":
        data_q = data_q.order_by(Seed.created_at.desc())
    elif sort == "most_liked":
        data_q = data_q.order_by(Seed.like_count.desc())
    elif sort == "most_collected":
        data_q = data_q.order_by(Seed.collection_count.desc())
    else:  # popular
        hot_score = _build_hot_score_expr()
        data_q = data_q.order_by(hot_score.desc())

    data_q = data_q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(data_q)
    seeds = result.unique().scalars().all()

    # Build response items
    items = []
    for seed in seeds:
        cover_url = None
        for ss in sorted(seed.screenshots, key=lambda s: s.sort_order):
            if ss.is_cover or not cover_url:
                cover_url = f"/uploads/{ss.file_path}"
                if ss.is_cover:
                    break

        tag_list = [
            {"key": st.tag.key, "label": st.tag.label, "icon": st.tag.icon}
            for st in seed.tags
        ]

        is_liked = False
        if current_user_id:
            like_check = await db.execute(
                select(Like).where(
                    Like.user_id == current_user_id, Like.seed_id == seed.id
                )
            )
            is_liked = like_check.scalar_one_or_none() is not None

        uploader = None
        if seed.uploader:
            ua = seed.uploader
            uploader = {
                "id": ua.id,
                "display_name": ua.display_name,
                "minecraft_username": ua.minecraft_username,
                "avatar_url": (
                    f"https://mc-heads.net/avatar/{ua.minecraft_uuid}/24"
                    if ua.minecraft_uuid
                    else None
                ),
                "owns_java_edition": ua.owns_java_edition,
            }

        items.append({
            "id": seed.id,
            "title": seed.title,
            "description_preview": (
                seed.description[:120] + "..."
                if len(seed.description) > 120
                else seed.description
            ),
            "cover_url": cover_url,
            "seed_value": seed.seed_value,
            "edition": seed.edition,
            "tested_version": seed.tested_version,
            "tags": tag_list,
            "like_count": seed.like_count,
            "collection_count": seed.collection_count,
            "view_count": seed.view_count,
            "is_liked": is_liked,
            "uploader": uploader,
            "created_at": seed.created_at.isoformat() + "Z" if seed.created_at else None,
        })

    return items, total


async def get_seed_detail(
    db: AsyncSession,
    seed_id: int,
    current_user_id: Optional[int] = None,
    session_key: Optional[str] = None,
) -> Optional[dict]:
    result = await db.execute(
        select(Seed)
        .options(
            selectinload(Seed.screenshots),
            selectinload(Seed.key_coords),
            selectinload(Seed.tags).joinedload(SeedTag.tag),
            selectinload(Seed.uploader),
        )
        .where(Seed.id == seed_id)
    )
    seed = result.unique().scalar_one_or_none()
    if not seed:
        return None

    # View counting (30 min dedup) — non-fatal
    if session_key:
        try:
            thirty_min_ago = datetime.utcnow() - timedelta(minutes=30)
            existing = await db.execute(
                select(SeedView).where(
                    SeedView.seed_id == seed_id,
                    SeedView.session_key == session_key,
                )
            )
            old = existing.scalar_one_or_none()
            if old and old.viewed_at >= thirty_min_ago:
                pass  # already counted within window
            else:
                if old:
                    await db.delete(old)
                db.add(SeedView(seed_id=seed_id, session_key=session_key))
                seed.view_count += 1
                await db.commit()
                await db.refresh(seed)
        except Exception:
            pass

    screenshots = sorted(seed.screenshots, key=lambda s: s.sort_order)
    tag_list = [
        {"key": st.tag.key, "label": st.tag.label, "icon": st.tag.icon}
        for st in seed.tags
    ]

    is_liked = False
    if current_user_id:
        like_check = await db.execute(
            select(Like).where(
                Like.user_id == current_user_id, Like.seed_id == seed.id
            )
        )
        is_liked = like_check.scalar_one_or_none() is not None

    uploader = None
    if seed.uploader:
        ua = seed.uploader
        uploader = {
            "id": ua.id,
            "display_name": ua.display_name,
            "minecraft_username": ua.minecraft_username,
            "avatar_url": (
                f"https://mc-heads.net/avatar/{ua.minecraft_uuid}/80"
                if ua.minecraft_uuid
                else None
            ),
            "owns_java_edition": ua.owns_java_edition,
        }

    return {
        "id": seed.id,
        "title": seed.title,
        "description": seed.description,
        "seed_value": seed.seed_value,
        "edition": seed.edition,
        "tested_version": seed.tested_version,
        "compatible_range": seed.compatible_range,
        "world_type": seed.world_type,
        "mod_env": seed.mod_env,
        "modpack_name": seed.modpack_name,
        "modpack_version": seed.modpack_version,
        "spawn_x": seed.spawn_x,
        "spawn_z": seed.spawn_z,
        "status": seed.status,
        "screenshots": [
            {
                "id": ss.id,
                "url": f"/uploads/{ss.file_path}",
                "is_cover": ss.is_cover,
                "sort_order": ss.sort_order,
            }
            for ss in screenshots
        ],
        "key_coords": [
            {"id": kc.id, "label": kc.label, "x": kc.x, "y": kc.y, "z": kc.z}
            for kc in seed.key_coords
        ],
        "tags": tag_list,
        "like_count": seed.like_count,
        "collection_count": seed.collection_count,
        "view_count": seed.view_count,
        "is_liked": is_liked,
        "uploader": uploader,
        "created_at": seed.created_at.isoformat() + "Z" if seed.created_at else None,
    }


async def create_seed(
    db: AsyncSession, data: SeedCreate, uploader_id: int
) -> Seed:
    # Parse seed_numeric
    seed_numeric = None
    try:
        seed_numeric = int(data.seed_value)
        if seed_numeric > 2**63 - 1 or seed_numeric < -(2**63):
            seed_numeric = None
    except (ValueError, OverflowError):
        seed_numeric = None

    # Resolve tag keys to IDs
    tag_result = await db.execute(
        select(Tag).where(Tag.key.in_(data.tags))
    )
    tag_objs = tag_result.scalars().all()

    seed = Seed(
        title=data.title,
        description=data.description,
        seed_value=data.seed_value,
        seed_numeric=seed_numeric,
        edition=data.edition,
        tested_version=data.tested_version,
        compatible_range=data.compatible_range,
        world_type=data.world_type,
        mod_env=data.mod_env,
        modpack_name=data.modpack_name,
        modpack_version=data.modpack_version,
        spawn_x=data.spawn_x,
        spawn_z=data.spawn_z,
        status="pending",
        uploader_id=uploader_id,
    )
    db.add(seed)
    await db.flush()

    # Associate screenshots
    for i, ss_id in enumerate(data.screenshot_ids):
        result = await db.execute(
            select(Screenshot).where(
                Screenshot.id == ss_id,
                Screenshot.uploader_id == uploader_id,
                Screenshot.status == "pending",
            )
        )
        ss = result.scalar_one_or_none()
        if ss:
            ss.seed_id = seed.id
            ss.status = "active"
            ss.sort_order = i
            if i == 0:
                ss.is_cover = True

    # Key coords
    for kc in data.key_coords:
        db.add(KeyCoord(
            seed_id=seed.id,
            label=kc.label,
            x=kc.x,
            y=kc.y,
            z=kc.z,
        ))

    # Tags
    for tag in tag_objs:
        db.add(SeedTag(seed_id=seed.id, tag_id=tag.id))

    await db.commit()
    await db.refresh(seed)
    return seed


async def toggle_like(
    db: AsyncSession, seed_id: int, user_id: int
) -> tuple[bool, int]:
    existing = await db.execute(
        select(Like).where(Like.user_id == user_id, Like.seed_id == seed_id)
    )
    like = existing.scalar_one_or_none()

    if like:
        await db.delete(like)
        liked = False
    else:
        db.add(Like(user_id=user_id, seed_id=seed_id))
        liked = True

    await db.flush()

    # Update counter
    new_count_result = await db.execute(
        select(func.count()).where(Like.seed_id == seed_id)
    )
    new_count = new_count_result.scalar() or 0

    seed_result = await db.execute(select(Seed).where(Seed.id == seed_id))
    seed = seed_result.scalar_one()
    seed.like_count = new_count

    await db.commit()
    return liked, new_count


async def check_duplicate(
    db: AsyncSession, seed_value: str, edition: str, tested_version: str
) -> Optional[int]:
    result = await db.execute(
        select(Seed.id).where(
            Seed.seed_value == seed_value,
            Seed.edition == edition,
            Seed.tested_version == tested_version,
            Seed.status != "rejected",
        )
    )
    return result.scalar_one_or_none()
