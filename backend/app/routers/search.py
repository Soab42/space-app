from fastapi import APIRouter, Query
from typing import Any
from ..vectorstore import global_similarity_search

router = APIRouter(prefix="/search", tags=["search"])

@router.get("/global")
def global_search(q: str = Query(..., min_length=2), k: int = 10) -> list[dict[str, Any]]:
    results = global_similarity_search(q, k=k)

    # Track seen publication IDs and their best scores
    seen_publications = {}
    out = []

    for doc, score in results:
        md = doc.metadata or {}
        publication_id = md.get("publication_id")

        # Skip if we've already seen this publication
        if publication_id in seen_publications:
            # If current result has higher score, replace the previous one
            if score > seen_publications[publication_id]["score"]:
                # Remove the old entry
                out = [item for item in out if item["publication_id"] != publication_id]
                # Add the new better result
                out.append({
                    "score": float(score),
                    "snippet": doc.page_content[:400],
                    "publication_id": publication_id,
                    "title": md.get("title"),
                    "chunk_id": md.get("chunk_id"),
                    "year": md.get("year"),
                    "organism": md.get("organism"),
                    "environment": md.get("environment"),
                })
                seen_publications[publication_id] = {"score": score}
        else:
            # First time seeing this publication
            out.append({
                "score": float(score),
                "snippet": doc.page_content[:400],
                "publication_id": publication_id,
                "title": md.get("title"),
                "chunk_id": md.get("chunk_id"),
                "year": md.get("year"),
                "organism": md.get("organism"),
                "environment": md.get("environment"),
            })
            seen_publications[publication_id] = {"score": score}

    # Sort by score in descending order
    out.sort(key=lambda x: x["score"], reverse=True)
    return out
