from fastapi import APIRouter, UploadFile, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Screenshot, User
from app.routers.auth import require_user
from app.services.storage import get_storage

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
EXT_MAP = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/screenshot", status_code=201)
async def upload_screenshot(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=422,
            detail={"code": "UNSUPPORTED_FORMAT", "message": "仅支持 JPG、PNG、WebP"},
        )

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail={"code": "FILE_TOO_LARGE", "message": "图片不能超过 5MB"},
        )

    ext = EXT_MAP.get(file.content_type, "webp")
    storage = get_storage()
    import io
    file_path = await storage.upload(io.BytesIO(content), f"upload.{ext}", file.content_type)

    # Strip /uploads/ prefix for DB storage
    db_path = file_path.replace("/uploads/", "", 1)

    screenshot = Screenshot(
        uploader_id=current_user.id,
        file_path=db_path,
        status="pending",
    )
    db.add(screenshot)
    await db.commit()
    await db.refresh(screenshot)

    return {
        "data": {
            "id": screenshot.id,
            "url": file_path,
        }
    }
