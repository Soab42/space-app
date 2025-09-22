from fastapi import APIRouter, Query
from typing import Any
from ..vectorstore import global_similarity_search

router = APIRouter(prefix="/search", tags=["search"])

@router.get("/global")
def global_search(q: str = Query(..., min_length=2), k: int = 10) -> list[dict[str, Any]]:
    results = global_similarity_search(q, k=k)
    out = []
    for doc, score in results:
        md = doc.metadata or {}
        out.append({
            "score": float(score),
            "snippet": doc.page_content[:400],
            "publication_id": md.get("publication_id"),
            "title": md.get("title"),
            "chunk_id": md.get("chunk_id"),
            "year": md.get("year"),
            "organism": md.get("organism"),
            "environment": md.get("environment"),
        })
    return out
