from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Liquid AI Chatbot Assignment"
    api_prefix: str = "/api"
    environment: str = "development"

    database_url: str = "sqlite:///./data/app.db"

    jwt_secret: str = Field(default="change-this-secret-before-deployment")
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "chat_history"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    ollama_base_url: str = "http://localhost:11434"
    liquid_model: str = "LiquidAI/lfm2.5-1.2b-instruct"
    llm_temperature: float = 0.3
    llm_top_k: int = 50
    memory_search_k: int = 4

    chatkit_domain_key: str = "local-dev"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
