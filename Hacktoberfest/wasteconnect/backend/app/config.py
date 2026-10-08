from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    gemma_provider: str = "google_ai_studio"
    gemma_api_key: str = ""
    gemma_model: str = "gemini-2.0-flash-exp"
    gemma_base_url: str = "http://localhost:11434/v1"
    hf_token: str = ""
    database_url: str = "sqlite+aiosqlite:///./wasteconnect.db"
    secret_key: str = "super-secret-key-change-in-prod"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    spaces_key: Optional[str] = None
    spaces_secret: Optional[str] = None
    spaces_bucket: Optional[str] = None
    spaces_region: Optional[str] = None
    spaces_endpoint: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
