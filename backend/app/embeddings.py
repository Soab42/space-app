# from __future__ import annotations

# from typing import Any

# from .config import get_settings


# def get_embedding_model() -> Any:
#     settings = get_settings()
#     provider = settings.EMBED_PROVIDER.lower()

#     if provider == "openai":
#         from langchain_openai import OpenAIEmbeddings

#         return OpenAIEmbeddings(model=settings.EMBED_MODEL)
#     elif provider == "ollama":
#         from langchain_community.embeddings import OllamaEmbeddings

#         return OllamaEmbeddings(model=settings.EMBED_MODEL)
#     else:
#         raise ValueError(f"Unsupported EMBED_PROVIDER: {settings.EMBED_PROVIDER}")

from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from app.config import get_settings

_settings = get_settings()

def get_embeddings():
    if _settings.EMBED_PROVIDER == "openai":
        return OpenAIEmbeddings(model=_settings.EMBED_MODEL, api_key=_settings.OPENAI_API_KEY)
    elif _settings.EMBED_PROVIDER == "ollama":
        return OllamaEmbeddings(model=_settings.EMBED_MODEL)
    else:
        raise ValueError("Unsupported EMBED_PROVIDER")
