from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Collection, CollectionSeed, Seed, User, Screenshot
from app.schemas import CollectionCreate, CollectionUpdate
from app.routers.auth import require_user, get_current_user
from app.services.auth import avatar_url

router = APIRouter(prefix="/collections", tags=["collections"])


def _make_collection_summary(c: Collection) -> dict:
    cover_url = None
    if c.cover_strategy == "manual" and c.cover_seed_id:
        # Would need to query the seed's cover, simplified for now
        pass
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "cover_url": cover_url,
        "seed_count": 0,  # Will be set below
        "is_public": c.is_public,
        "sort_order": c.sort_order,
        "created_at": c.created_at.isoformat() + "Z" if c.created_at else None,
        "updated_at": c.updated_at.isoformat() + "Z" if c.updated_at else None,
    }


def _make_seed_list_item(seed: Seed) -> dict:
    cover_url = None
    for ss in sorted(seed.screenshots, key=lambda s: s.sort_order):
        if ss.is_cover or not cover_url:
            cover_url = f"/uploads/{ss.file_path}"
            if ss.is_cover:
                break
    return {
        "id": seed.id,
        "title": seed.title,
        "description_preview": seed.description[:120] + "..." if len(seed.description) > 120 else seed.description,
        "cover_url": cover_url,
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
    }


@router.get("")
async def list_collections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    result = await db.execute(
        select(Collection)
        .where(Collection.user_id == current_user.id)
        .order_by(Collection.sort_order, Collection.created_at.desc())
    )
    collections = result.scalars().all()

    items = []
    for c in collections:
        count_result = await db.execute(
            select(func.count()).where(CollectionSeed.collection_id == c.id)
        )
        seed_count = count_result.scalar() or 0
        item = _make_collection_summary(c)
        item["seed_count"] = seed_count
        items.append(item)

    return {"data": items}


@router.post("", status_code=201)
async def create_collection(
    data: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    collection = Collection(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        is_public=data.is_public,
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)
    item = _make_collection_summary(collection)
    return {"data": item}


@router.get("/{collection_id}")
async def get_collection(
    collection_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, le=48),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    result = await db.execute(
        select(Collection).options(selectinload(Collection.user)).where(Collection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "收藏夹不存在"})
    if not collection.is_public and (not current_user or collection.user_id != current_user.id):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "无权访问此收藏夹"})

    owner = None
    if collection.user:
        u = collection.user
        owner = {
            "id": u.id,
            "display_name": u.display_name,
            "minecraft_username": u.minecraft_username,
            "avatar_url": avatar_url(u.minecraft_uuid, 28),
            "owns_java_edition": u.owns_java_edition,
        }

    # Count seeds
    count_q = select(func.count()).where(CollectionSeed.collection_id == collection_id)
    total = (await db.execute(count_q)).scalar() or 0

    # Get seeds
    seeds_q = (
        select(Seed)
        .join(CollectionSeed)
        .options(selectinload(Seed.screenshots))
        .where(CollectionSeed.collection_id == collection_id)
        .order_by(CollectionSeed.added_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    seeds_result = await db.execute(seeds_q)
    seeds = seeds_result.unique().scalars().all()

    seed_items = [_make_seed_list_item(s) for s in seeds]
    pages = max(1, (total + page_size - 1) // page_size)

    return {
        "data": {
            "id": collection.id,
            "name": collection.name,
            "description": collection.description,
            "cover_strategy": collection.cover_strategy,
            "cover_seed_id": collection.cover_seed_id,
            "cover_url": None,
            "is_public": collection.is_public,
            "owner": owner,
            "seeds": seed_items,
            "meta": {"page": page, "page_size": page_size, "total": total, "pages": pages},
        }
    }


@router.put("/{collection_id}")
async def update_collection(
    collection_id: int,
    data: CollectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "收藏夹不存在"})
    if collection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "无权编辑此收藏夹"})

    if data.name is not None:
        collection.name = data.name
    if data.description is not None:
        collection.description = data.description
    if data.cover_strategy is not None:
        collection.cover_strategy = data.cover_strategy
        if data.cover_strategy != "manual":
            collection.cover_seed_id = None
    if data.cover_seed_id is not None:
        collection.cover_seed_id = data.cover_seed_id
    if data.is_public is not None:
        collection.is_public = data.is_public
    if data.sort_order is not None:
        collection.sort_order = data.sort_order

    from datetime import datetime
    collection.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(collection)
    return {"data": _make_collection_summary(collection)}


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "收藏夹不存在"})
    if collection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "无权删除此收藏夹"})
    await db.delete(collection)
    await db.commit()
    return {"data": {"message": "收藏夹已删除"}}


@router.post("/{collection_id}/seeds/{seed_id}", status_code=201)
async def add_seed_to_collection(
    collection_id: int,
    seed_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "收藏夹不存在"})
    if collection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "无权操作此收藏夹"})

    existing = await db.execute(
        select(CollectionSeed).where(
            CollectionSeed.collection_id == collection_id,
            CollectionSeed.seed_id == seed_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail={"code": "ALREADY_IN_COLLECTION", "message": "该种子已在此收藏夹中"})

    db.add(CollectionSeed(collection_id=collection_id, seed_id=seed_id))

    # Update counter
    seed_result = await db.execute(select(Seed).where(Seed.id == seed_id))
    seed = seed_result.scalar_one()
    seed.collection_count += 1

    from datetime import datetime
    collection.updated_at = datetime.utcnow()
    await db.commit()

    return {
        "data": {
            "collection_id": collection_id,
            "seed_id": seed_id,
            "added_at": datetime.utcnow().isoformat() + "Z",
        }
    }


@router.delete("/{collection_id}/seeds/{seed_id}")
async def remove_seed_from_collection(
    collection_id: int,
    seed_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "收藏夹不存在"})
    if collection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "无权操作此收藏夹"})

    cs_result = await db.execute(
        select(CollectionSeed).where(
            CollectionSeed.collection_id == collection_id,
            CollectionSeed.seed_id == seed_id,
        )
    )
    cs = cs_result.scalar_one_or_none()
    if not cs:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "该种子不在收藏夹中"})

    await db.delete(cs)

    # Update counter
    seed_result = await db.execute(select(Seed).where(Seed.id == seed_id))
    seed = seed_result.scalar_one()
    seed.collection_count = max(0, seed.collection_count - 1)

    # Reset manual cover if it was this seed
    if collection.cover_strategy == "manual" and collection.cover_seed_id == seed_id:
        collection.cover_strategy = "last"
        collection.cover_seed_id = None

    await db.commit()
    return {"data": {"message": "种子已从收藏夹移除"}}
