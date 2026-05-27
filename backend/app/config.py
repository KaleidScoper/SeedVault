from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # App
    APP_ENV: str = "development"
    ALLOW_DEV_LOGIN: bool = False
    SECRET_KEY: str = "change-me-in-production"
    BASE_URL: str = "http://localhost:8000"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///data.db"

    # Upload
    STORAGE_BACKEND: str = "local"
    UPLOAD_DIR: str = "./uploads"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # Microsoft OAuth
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/callback"

    # JWT
    JWT_EXPIRE_SECONDS: int = 604800  # 7 days

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "development"


settings = Settings()
