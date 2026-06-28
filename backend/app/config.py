"""Application settings, loaded from environment / .env via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_provider: str = "openrouter"  # openrouter | openai
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    ollama_base_url: str = "http://localhost:11434"

    # Embeddings
    embedding_provider: str = "local"  # local | openai
    embedding_model: str = "all-MiniLM-L6-v2"

    # Data sources
    coingecko_api_key: str = ""
    cryptopanic_api_key: str = ""

    # Storage
    chroma_persist_dir: str = "./data/chroma"

    # Cache (optional; disabled when empty)
    redis_url: str = ""

    # News
    news_lookback_hours: int = 48
    max_news_items: int = 40

    # CORS / frontend
    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
