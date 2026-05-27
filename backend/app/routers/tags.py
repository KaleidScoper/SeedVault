from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Tag

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("")
async def get_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tag).order_by(Tag.category, Tag.id))
    tags = result.scalars().all()
    return {
        "data": [
            {"key": t.key, "label": t.label, "icon": t.icon, "category": t.category}
            for t in tags
        ]
    }
