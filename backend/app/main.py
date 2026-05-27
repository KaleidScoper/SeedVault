import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, async_session
from app.seed_data import seed_all
from app.routers import auth, seeds, upload, tags, versions, users, notifications, collections, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Run seed data
    async with async_session() as session:
        await seed_all(session)
    yield


app = FastAPI(
    title="SeedVault API",
    description="Minecraft 种子共享平台",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploads
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Routers
api_prefix = "/api/v1"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(seeds.router, prefix=api_prefix)
app.include_router(upload.router, prefix=api_prefix)
app.include_router(tags.router, prefix=api_prefix)
app.include_router(versions.router, prefix=api_prefix)
app.include_router(users.router, prefix=api_prefix)
app.include_router(notifications.router, prefix=api_prefix)
app.include_router(collections.router, prefix=api_prefix)
app.include_router(admin.router, prefix=api_prefix)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
