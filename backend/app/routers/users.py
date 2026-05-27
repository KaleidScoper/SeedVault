from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import User, Seed, Like, SeedTag, Screenshot, Tag
from app.routers.auth import require_user
from app.services.auth import avatar_url, get_user_by_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}")
async def get_user_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "用户不存在"})

    seed_count_result = await db.execute(
        select(func.count()).where(Seed.uploader_id == user_id, Seed.status == "approved")
    )
    approved_count = seed_count_result.scalar() or 0

    return {
        "data": {
            "id": user.id,
            "display_name": user.display_name,
            "minecraft_username": user.minecraft_username,
            "avatar_url": avatar_url(user.minecraft_uuid, 80),
            "owns_java_edition": user.owns_java_edition,
            "approved_seed_count": approved_count,
            "created_at": user.created_at.isoformat() + "Z" if user.created_at else None,
        }
    }


@router.get("/me/seeds")
async def my_seeds(
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, le=48),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    conditions = [Seed.uploader_id == current_user.id]
    if status:
        conditions.append(Seed.status == status)

    count_q = select(func.count()).select_from(Seed).where(*conditions)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Seed)
        .where(*conditions)
        .order_by(Seed.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    seeds = result.scalars().all()

    items = []
    for seed in seeds:
        items.append({
            "id": seed.id,
            "title": seed.title,
            "description_preview": seed.description[:120],
            "cover_url": None,
            "seed_value": seed.seed_value,
            "edition": seed.edition,
            "tested_version": seed.tested_version,
            "tags": [],
            "like_count": seed.like_count,
            "collection_count": seed.collection_count,
            "view_count": seed.view_count,
            "is_liked": False,
            "uploader": None,
            "created_at": seed.created_at.isoformat() + "Z" if seed.created_at else None,
        })

    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": items,
        "meta": {"page": page, "page_size": page_size, "total": total, "pages": pages},
    }


@router.get("/me/bookmarks")
async def my_bookmarks(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, le=48),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    count_q = select(func.count()).where(Like.user_id == current_user.id)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Seed)
        .join(Like)
        .where(Like.user_id == current_user.id)
        .order_by(Like.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    seeds = result.scalars().all()

    items = []
    for seed in seeds:
        items.append({
            "id": seed.id,
            "title": seed.title,
            "description_preview": seed.description[:120],
            "cover_url": None,
            "seed_value": seed.seed_value,
            "edition": seed.edition,
            "tested_version": seed.tested_version,
            "tags": [],
            "like_count": seed.like_count,
            "collection_count": seed.collection_count,
            "view_count": seed.view_count,
            "is_liked": True,
            "uploader": None,
            "created_at": seed.created_at.isoformat() + "Z" if seed.created_at else None,
        })

    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": items,
        "meta": {"page": page, "page_size": page_size, "total": total, "pages": pages},
    }


@router.post("/me/bookmarks/merge")
async def merge_bookmarks(
    seed_ids: list[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    merged = 0
    for seed_id in seed_ids:
        existing = await db.execute(
            select(Like).where(Like.user_id == current_user.id, Like.seed_id == seed_id)
        )
        if not existing.scalar_one_or_none():
            db.add(Like(user_id=current_user.id, seed_id=seed_id))
            merged += 1
    await db.commit()
    return {"data": {"merged_count": merged, "message": f"已合并 {merged} 条收藏"}}
