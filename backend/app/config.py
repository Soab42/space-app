# from __future__ import annotations

# from pathlib import Path
# from typing import Optional

# from dotenv import load_dotenv
# from pydantic import BaseModel
# from pydantic_settings import BaseSettings, SettingsConfigDict


# # Ensure we load backend/.env once at import time
# ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
# load_dotenv(dotenv_path=ENV_PATH, override=False)


# class Settings(BaseSettings):
#     # FastAPI
#     PORT: int = 8000
#     CORS_ORIGINS: str = "http://localhost:3000"

#     # Database
#     DATABASE_URL: str

#     # Embeddings / LLM
#     EMBED_PROVIDER: str = "openai"  # or: ollama
#     EMBED_MODEL: str = "text-embedding-3-small"
#     OPENAI_API_KEY: Optional[str] = None

#     LLM_PROVIDER: str = "openai"  # or: ollama
#     LLM_MODEL: str = "gpt-4o-mini"

#     # LangSmith
#     LANGCHAIN_TRACING_V2: bool = False
#     LANGCHAIN_PROJECT: Optional[str] = None
#     LANGCHAIN_API_KEY: Optional[str] = None

#     model_config = SettingsConfigDict(env_file=str(ENV_PATH), env_file_encoding="utf-8", extra="ignore")


# class AppConfig(BaseModel):
#     settings: Settings


# def get_settings() -> Settings:
#     # Singleton-esque pattern to avoid re-parsing env repeatedly
#     global _settings
#     try:
#         return _settings  # type: ignore[name-defined]
#     except NameError:
#         _settings = Settings()  # type: ignore[assignment]
#         return _settings

import os
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()


class Settings:
    def __init__(self):
        # Core
        self.PORT: int = int(os.getenv("PORT", 8000))
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://root:1234@localhost:32768/nasa_biosc")
        self.CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")

        # Embeddings / LLM
        self.EMBED_PROVIDER: str = os.getenv("EMBED_PROVIDER", "ollama")  # openai | ollama
        self.EMBED_MODEL: str = os.getenv("EMBED_MODEL", "nomic-embed-text")
        self.OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

        self.LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")      # openai | ollama
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", "mistral")

        # Paths
        self.INDICES_DIR: str = os.path.abspath(os.path.join(os.getcwd(), "..", "data", "indices"))
        self.UPLOADS_DIR: str = os.path.abspath(os.path.join(os.getcwd(), "..", "uploads"))
        os.makedirs(self.INDICES_DIR, exist_ok=True)
        os.makedirs(self.UPLOADS_DIR, exist_ok=True)

        # LangSmith
        self.LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() in ("true", "1", "yes")
        self.LANGCHAIN_PROJECT: str | None = os.getenv("LANGCHAIN_PROJECT")
        self.LANGCHAIN_API_KEY: str | None = os.getenv("LANGCHAIN_API_KEY")

@lru_cache
def get_settings():
    s = Settings()
    # os.makedirs(s.INDICES_DIR, exist_ok=True)
    # os.makedirs(s.UPLOADS_DIR, exist_ok=True)
    return s
