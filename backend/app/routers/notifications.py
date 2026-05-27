from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Notification, User
from app.routers.auth import require_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def get_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    count_q = select(func.count()).where(Notification.user_id == current_user.id)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    notifs = result.scalars().all()

    items = [
        {
            "id": n.id,
            "type": n.type,
            "message": n.message,
            "detail": n.detail,
            "seed_id": n.seed_id,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() + "Z" if n.created_at else None,
        }
        for n in notifs
    ]
    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": items,
        "meta": {"page": page, "page_size": page_size, "total": total, "pages": pages},
    }


@router.post("/{notif_id}/read")
async def mark_read(
    notif_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "通知不存在"})
    notif.is_read = True
    await db.commit()
    return {"data": {"id": notif.id, "is_read": True}}
