import os
from typing import List, Optional
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from .embeddings import get_embeddings
from .config import get_settings

settings = get_settings()

def _pub_dir(pub_id: int) -> str:
    d = os.path.join(settings.INDICES_DIR, str(pub_id))
    os.makedirs(d, exist_ok=True)
    return d

def _global_dir() -> str:
    d = os.path.join(settings.INDICES_DIR, "global")
    os.makedirs(d, exist_ok=True)
    return d

# -------- Per-publication FAISS --------
def save_faiss_for_publication(pub_id: int, docs: List[Document]) -> None:
    embeddings = get_embeddings()
    vs = FAISS.from_documents(docs, embeddings)
    vs.save_local(_pub_dir(pub_id))
   

def load_faiss_for_publication(pub_id: int) -> FAISS:
    embeddings = get_embeddings()
    d = _pub_dir(pub_id)
    return FAISS.load_local(d, embeddings, allow_dangerous_deserialization=True)

# -------- Global FAISS --------
def _load_global_vs(embeddings=None) -> Optional[FAISS]:
    embeddings = embeddings or get_embeddings()
    d = _global_dir()
    try:
        return FAISS.load_local(d, embeddings, allow_dangerous_deserialization=True)
    except Exception:
        return None

def upsert_global_documents(docs: List[Document]) -> None:
    embeddings = get_embeddings()
    gvs = _load_global_vs(embeddings)
    if gvs is None:
        gvs = FAISS.from_documents(docs, embeddings)
    else:
        gvs.add_documents(docs)
    gvs.save_local(_global_dir())

def global_similarity_search(query: str, k: int = 10) -> List[Document]:
    embeddings = get_embeddings()
    gvs = _load_global_vs(embeddings)
    if gvs is None:
        return []
    return gvs.similarity_search_with_score(query, k=k)

def add_context_to_publication(publication_id: int, additional_context: str):
    from .ingestion import chunk_text
    from .db import SessionLocal
    from .models import Publication
    embeddings = get_embeddings()

    db = SessionLocal()
    publication = db.get(Publication, publication_id)
    if not publication:
        raise Exception("Publication not found")

    docs = chunk_text(additional_context)
    for i, d in enumerate(docs):
        d.metadata.update({
            "publication_id": publication.id,
            "title": publication.title,
            "chunk_id": i + 1, # This might need adjustment if there are existing chunks
            "year": publication.date_year,
            "organism": publication.organism,
            "environment": publication.environment,
            "type": "publication_chunk"
        })

    # Add to per-publication FAISS
    try:
        vs = load_faiss_for_publication(publication.id)
        vs.add_documents(docs)
    except Exception as e:
        vs = FAISS.from_documents(docs, embeddings)
    
    vs.save_local(_pub_dir(publication.id))


    # Add to global FAISS
    upsert_global_documents(docs)

    db.close()