from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "MedIntel AI"
    debug: bool = False
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 1440

    database_url: str = "postgresql+asyncpg://medintel:medintel@localhost:5432/medintel"
    redis_url: str = "redis://localhost:6379/0"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_vision_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "models/text-embedding-004"

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = "medintel-uploads"
    s3_endpoint_url: str | None = None

    faiss_index_path: str = "./data/faiss_index"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
