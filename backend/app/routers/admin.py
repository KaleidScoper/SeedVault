from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.database import get_db
from app.models import Seed, User, Version, Notification, Report
from app.schemas import VersionCreate
from app.routers.auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/seeds/pending")
async def pending_seeds(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, le=48),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    count_q = select(func.count()).where(Seed.status == "pending")
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Seed)
        .where(Seed.status == "pending")
        .order_by(Seed.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    seeds = result.scalars().all()

    items = []
    for seed in seeds:
        uploader = None
        if seed.uploader:
            u = seed.uploader
            uploader = {"id": u.id, "display_name": u.display_name}
        items.append({
            "id": seed.id,
            "title": seed.title,
            "seed_value": seed.seed_value,
            "edition": seed.edition,
            "tested_version": seed.tested_version,
            "cover_url": None,
            "uploader": uploader,
            "created_at": seed.created_at.isoformat() + "Z" if seed.created_at else None,
        })

    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": items,
        "meta": {"page": page, "page_size": page_size, "total": total, "pages": pages},
    }


@router.post("/seeds/{seed_id}/approve")
async def approve_seed(
    seed_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(Seed).where(Seed.id == seed_id))
    seed = result.scalar_one_or_none()
    if not seed:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "种子不存在"})

    seed.status = "approved"
    seed.approved_at = datetime.utcnow()
    seed.approved_by = admin.id

    db.add(Notification(
        user_id=seed.uploader_id,
        type="seed_approved",
        message=f"您的投稿「{seed.title}」已通过审核",
        seed_id=seed.id,
    ))
    await db.commit()
    return {"data": {"id": seed.id, "status": "approved", "message": "审核已通过"}}


@router.post("/seeds/{seed_id}/reject")
async def reject_seed(
    seed_id: int,
    reason: str = Query(""),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(Seed).where(Seed.id == seed_id))
    seed = result.scalar_one_or_none()
    if not seed:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "种子不存在"})

    seed.status = "rejected"
    seed.rejection_reason = reason

    db.add(Notification(
        user_id=seed.uploader_id,
        type="seed_rejected",
        message=f"您的投稿「{seed.title}」未通过审核",
        detail=reason,
        seed_id=seed.id,
    ))
    await db.commit()
    return {"data": {"id": seed.id, "status": "rejected", "reason": reason}}


@router.get("/users")
async def list_users(
    q: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    conditions = []
    if q:
        conditions.append(
            (User.display_name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%"))
        )

    count_q = select(func.count()).select_from(User)
    if conditions:
        count_q = count_q.where(*conditions)
    total = (await db.execute(count_q)).scalar() or 0

    uq = select(User).order_by(User.created_at.desc())
    if conditions:
        uq = uq.where(*conditions)
    uq = uq.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(uq)
    users = result.scalars().all()

    items = []
    for u in users:
        seed_count_result = await db.execute(
            select(func.count()).where(Seed.uploader_id == u.id)
        )
        seed_count = seed_count_result.scalar() or 0
        items.append({
            "id": u.id,
            "display_name": u.display_name,
            "email": u.email,
            "minecraft_username": u.minecraft_username,
            "owns_java_edition": u.owns_java_edition,
            "role": u.role,
            "is_banned": u.is_banned,
            "seed_count": seed_count,
            "created_at": u.created_at.isoformat() + "Z" if u.created_at else None,
        })

    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": items,
        "meta": {"page": page, "page_size": page_size, "total": total, "pages": pages},
    }


@router.post("/users/{user_id}/ban")
async def toggle_ban(
    user_id: int,
    banned: bool = Query(True),
    reason: str = Query(""),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "用户不存在"})
    if user.role == "admin":
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "不能封禁管理员"})

    user.is_banned = banned
    await db.commit()
    msg = "用户已被封禁" if banned else "用户已解封"
    return {"data": {"id": user.id, "is_banned": banned, "message": msg}}


@router.post("/versions", status_code=201)
async def add_version(
    data: VersionCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if data.is_latest:
        await db.execute(
            update(Version)
            .where(Version.edition == data.edition)
            .values(is_latest=False)
        )

    # Compute sort order
    max_order_result = await db.execute(
        select(func.max(Version.sort_order)).where(Version.edition == data.edition)
    )
    max_order = max_order_result.scalar() or 0

    version = Version(
        edition=data.edition,
        version=data.version,
        is_latest=data.is_latest,
        sort_order=max_order + 1,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return {
        "data": {
            "id": version.id,
            "edition": version.edition,
            "version": version.version,
            "message": "版本号已添加",
        }
    }


@router.delete("/versions/{version_id}")
async def delete_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(Version).where(Version.id == version_id))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "版本号不存在"})
    await db.delete(version)
    await db.commit()
    return {"data": {"message": "版本号已删除"}}


@router.get("/reports")
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, le=48),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    count_q = select(func.count()).where(Report.status == "pending")
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Report)
        .where(Report.status == "pending")
        .order_by(Report.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    reports = result.scalars().all()

    items = []
    for r in reports:
        seed_result = await db.execute(select(Seed).where(Seed.id == r.seed_id))
        seed = seed_result.scalar_one_or_none()
        reporter = None
        if r.reporter_id:
            ur = await db.execute(select(User).where(User.id == r.reporter_id))
            u = ur.scalar_one_or_none()
            if u:
                reporter = {"id": u.id, "display_name": u.display_name}
        items.append({
            "id": r.id,
            "seed_id": r.seed_id,
            "seed_title": seed.title if seed else "(已删除)",
            "reporter": reporter,
            "reason": r.reason,
            "detail": r.detail,
            "status": r.status,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
        })

    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": items,
        "meta": {"page": page, "page_size": page_size, "total": total, "pages": pages},
    }


@router.post("/reports/{report_id}/review")
async def review_report(
    report_id: int,
    action: str = Query(..., pattern="^(dismiss|remove_seed)$"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    rq = await db.execute(select(Report).where(Report.id == report_id))
    report = rq.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "举报不存在"})

    report.status = "reviewed" if action == "dismiss" else "reviewed"

    if action == "remove_seed":
        sq = await db.execute(select(Seed).where(Seed.id == report.seed_id))
        seed = sq.scalar_one_or_none()
        if seed:
            seed.status = "rejected"
            seed.rejection_reason = "因举报被移除"
            db.add(Notification(
                user_id=seed.uploader_id,
                type="seed_rejected",
                message=f"您的投稿「{seed.title}」因举报被移除",
                seed_id=seed.id,
            ))

    await db.commit()
    return {"data": {"id": report.id, "status": report.status, "message": "已处理"}}
