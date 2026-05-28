from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Comment
from app.schemas import SeedCreate, ReportCreate, CommentInput
from app.services.seeds import (
    list_seeds, get_seed_detail, create_seed, toggle_like, check_duplicate,
)
from app.services.auth import hash_session_key
from app.routers.auth import get_current_user, require_user
from app.models import User, Report

router = APIRouter(prefix="/seeds", tags=["seeds"])


@router.get("")
async def get_seeds(
    request: Request,
    edition: str = Query(None),
    version: str = Query(None),
    world_type: str = Query(None),
    tags: str = Query(None),
    mod_env: str = Query(None),
    sort: str = Query("popular"),
    q: str = Query(None),
    uploader_id: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, le=48),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    tag_list = tags.split(",") if tags else None
    items, total = await list_seeds(
        db,
        edition=edition,
        version=version,
        world_type=world_type,
        tags=tag_list,
        mod_env=mod_env,
        sort=sort,
        q=q,
        uploader_id=uploader_id,
        page=page,
        page_size=page_size,
        current_user_id=current_user.id if current_user else None,
    )
    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": items,
        "meta": {"page": page, "page_size": page_size, "total": total, "pages": pages},
    }


@router.get("/{seed_id}")
async def get_seed(
    seed_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    # Build session key for view dedup
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "unknown")
    sk = hash_session_key(seed_id, ip, ua)

    detail = await get_seed_detail(
        db, seed_id,
        current_user_id=current_user.id if current_user else None,
        session_key=sk,
    )
    if not detail:
        raise HTTPException(status_code=404, detail={"code": "SEED_NOT_FOUND", "message": "该种子不存在或已被删除"})
    return {"data": detail}


@router.post("", status_code=201)
async def submit_seed(
    data: SeedCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    existing_id = await check_duplicate(db, data.seed_value, data.edition, data.tested_version)
    if existing_id:
        raise HTTPException(
            status_code=409,
            detail={"code": "DUPLICATE_SEED", "message": "该种子已有投稿", "existing_id": existing_id},
        )
    seed = await create_seed(db, data, current_user.id)
    return {
        "data": {
            "id": seed.id,
            "status": "pending",
            "message": "投稿已提交，等待审核",
        }
    }


@router.post("/{seed_id}/like")
async def like_seed(
    seed_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    liked, count = await toggle_like(db, seed_id, current_user.id)
    return {"data": {"liked": liked, "like_count": count}}


@router.post("/{seed_id}/report", status_code=201)
async def report_seed(
    seed_id: int,
    data: ReportCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    ip_hash = None
    if not current_user:
        ip = request.client.host if request.client else "unknown"
        import hashlib
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:64]

    report = Report(
        seed_id=seed_id,
        reporter_id=current_user.id if current_user else None,
        reporter_ip_hash=ip_hash,
        reason=data.reason,
        detail=data.detail,
    )
    db.add(report)
    await db.commit()
    return {"data": {"message": "举报已提交，感谢您的贡献"}}


@router.get("/{seed_id}/comments")
async def get_comments(
    seed_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
):
    count_q = select(func.count()).where(
        Comment.seed_id == seed_id, Comment.deleted_at.is_(None)
    )
    total = (await db.execute(count_q)).scalar() or 0

    comments_q = (
        select(Comment)
        .where(Comment.seed_id == seed_id, Comment.deleted_at.is_(None))
        .order_by(Comment.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(comments_q)
    comments = result.scalars().all()

    items = []
    for c in comments:
        author = None
        if c.author:
            a = c.author
            author = {
                "id": a.id,
                "display_name": a.display_name,
                "minecraft_username": a.minecraft_username,
                "avatar_url": (
                    f"https://mc-heads.net/avatar/{a.minecraft_uuid}/28"
                    if a.minecraft_uuid else None
                ),
                "owns_java_edition": a.owns_java_edition,
            }
        items.append({
            "id": c.id,
            "content": c.content,
            "author": author,
            "created_at": c.created_at.isoformat() + "Z" if c.created_at else None,
        })

    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": items,
        "meta": {"page": page, "page_size": page_size, "total": total, "pages": pages},
    }


@router.post("/{seed_id}/comments", status_code=201)
async def post_comment(
    seed_id: int,
    data: CommentInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    comment = Comment(
        seed_id=seed_id,
        author_id=current_user.id,
        content=data.content,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    author = {
        "id": current_user.id,
        "display_name": current_user.display_name,
        "minecraft_username": current_user.minecraft_username,
        "avatar_url": (
            f"https://mc-heads.net/avatar/{current_user.minecraft_uuid}/28"
            if current_user.minecraft_uuid else None
        ),
        "owns_java_edition": current_user.owns_java_edition,
    }
    return {
        "data": {
            "id": comment.id,
            "content": comment.content,
            "author": author,
            "created_at": comment.created_at.isoformat() + "Z" if comment.created_at else None,
        }
    }


@router.delete("/{seed_id}/comments/{comment_id}")
async def delete_comment(
    seed_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id, Comment.seed_id == seed_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "评论不存在"})
    if comment.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "只能删除自己的评论"})
    from datetime import datetime
    comment.deleted_at = datetime.utcnow()
    await db.commit()
    return {"data": {"message": "评论已删除"}}
