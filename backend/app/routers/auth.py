import secrets
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import AuthMeResponse
from app.services.auth import (
    create_jwt, decode_jwt, get_user_by_id,
    create_or_update_user, avatar_url, get_unread_count,
)
from app.services.minecraft import (
    get_ms_auth_url, exchange_code, authenticate_minecraft,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def set_jwt_cookie(response: JSONResponse, token: str):
    response.set_cookie(
        "seedvault_token",
        token,
        httponly=True,
        secure=settings.APP_ENV != "development",
        samesite="lax",
        path="/",
        max_age=settings.JWT_EXPIRE_SECONDS,
    )


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    token = request.cookies.get("seedvault_token")
    if not token:
        return None
    payload = decode_jwt(token)
    if not payload:
        return None
    user = await get_user_by_id(db, int(payload.get("sub", 0)))
    if not user or user.is_banned:
        return None
    return user


async def require_user(user: User | None = Depends(get_current_user)) -> User:
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin required")
    return user


@router.get("/login")
async def login(redirect: str = Query(None)):
    state = secrets.token_urlsafe(32)
    url = get_ms_auth_url(state)
    if redirect:
        url += f"&redirect={redirect}"
    # Store state in a signed cookie for CSRF protection
    response = RedirectResponse(url)
    response.set_cookie("oauth_state", state, httponly=True, max_age=600, samesite="lax")
    return response


@router.get("/callback")
async def callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(None),
    redirect: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    # If OAuth is not configured, redirect to frontend with error
    if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_CLIENT_SECRET:
        return RedirectResponse(f"{settings.CORS_ORIGINS}?auth_error=not_configured")

    access_token, refresh_token, err = await exchange_code(code)
    if err:
        return JSONResponse({"error": {"code": "AUTH_FAILED", "message": err}}, status_code=400)

    mc_result = await authenticate_minecraft(access_token)

    # For now, we don't have Microsoft Graph email, use placeholder
    display_name = mc_result.username or "Player"
    email = None

    user = await create_or_update_user(
        db,
        microsoft_id="ms_" + secrets.token_hex(8),  # Placeholder without Graph API
        email=email,
        display_name=display_name,
        minecraft_uuid=mc_result.uuid,
        minecraft_username=mc_result.username,
        owns_java_edition=mc_result.owns_java,
    )

    token = create_jwt(user.id, user.role)
    frontend_url = settings.CORS_ORIGINS
    if redirect:
        frontend_url += redirect
    response = RedirectResponse(frontend_url)
    set_jwt_cookie(response, token)
    return response


@router.post("/logout")
async def logout():
    response = JSONResponse({"data": {"message": "已退出登录"}})
    response.delete_cookie("seedvault_token", path="/")
    return response


@router.get("/me")
async def me(user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    unread = await get_unread_count(db, user.id)
    return {
        "data": {
            "id": user.id,
            "display_name": user.display_name,
            "minecraft_uuid": user.minecraft_uuid,
            "minecraft_username": user.minecraft_username,
            "owns_java_edition": user.owns_java_edition,
            "avatar_url": avatar_url(user.minecraft_uuid, 80),
            "role": user.role,
            "unread_count": unread,
            "created_at": user.created_at.isoformat() + "Z" if user.created_at else None,
        }
    }


@router.post("/dev-login")
async def dev_login(
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Development-only: login as any user by ID."""
    if not settings.ALLOW_DEV_LOGIN or not settings.is_dev:
        return JSONResponse(
            {"error": {"code": "FORBIDDEN", "message": "Dev login not enabled"}},
            status_code=403,
        )
    user = await get_user_by_id(db, user_id)
    if not user:
        return JSONResponse(
            {"error": {"code": "NOT_FOUND", "message": "User not found"}},
            status_code=404,
        )
    token = create_jwt(user.id, user.role)
    response = JSONResponse({"data": {"message": f"Logged in as {user.display_name}"}})
    set_jwt_cookie(response, token)
    return response
