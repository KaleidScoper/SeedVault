import os
import uuid
import aiofiles
from typing import BinaryIO
from app.config import settings


class LocalStorage:
    async def upload(self, file: BinaryIO, filename: str, content_type: str) -> str:
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "webp"
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        rel_path = os.path.join("screenshots", stored_name)
        abs_path = os.path.join(settings.UPLOAD_DIR, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        async with aiofiles.open(abs_path, "wb") as f:
            await f.write(file.read())
        return f"/uploads/{rel_path}"

    async def delete(self, file_path: str) -> None:
        # file_path is like /uploads/screenshots/xxx.webp
        rel = file_path.lstrip("/").replace("uploads/", "", 1)
        abs_path = os.path.join(settings.UPLOAD_DIR, rel)
        if os.path.exists(abs_path):
            os.remove(abs_path)


_storage = LocalStorage()


def get_storage() -> LocalStorage:
    return _storage
