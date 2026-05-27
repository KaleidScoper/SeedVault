from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Version

router = APIRouter(prefix="/versions", tags=["versions"])


@router.get("")
async def get_versions(
    edition: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Version).order_by(Version.sort_order.desc())
    if edition:
        q = q.where(Version.edition == edition)
    result = await db.execute(q)
    versions = result.scalars().all()
    return {
        "data": [
            {
                "id": v.id,
                "edition": v.edition,
                "version": v.version,
                "is_latest": v.is_latest,
                "sort_order": v.sort_order,
            }
            for v in versions
        ]
    }
