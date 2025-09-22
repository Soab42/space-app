# from __future__ import annotations

# from pydantic import BaseModel
# from fastapi import APIRouter

# from ..rag_graph import answer_question


# class QARequest(BaseModel):
#     query: str


# router = APIRouter(prefix="/qa", tags=["qa"])


# @router.post("/")
# def ask_qa(req: QARequest):
#     return answer_question(req.query)

from fastapi import APIRouter, HTTPException
from ..schemas import QABody
from ..rag_graph import build_qa_graph
from ..vectorstore import load_faiss_for_publication
import os

router = APIRouter(prefix="/qa", tags=["qa"])
graph = build_qa_graph()

@router.post("/single-doc")
def qa_single_doc(body: QABody):
    # sanity: ensure index exists
    try:
        _ = load_faiss_for_publication(body.publication_id)
    except Exception:
        raise HTTPException(404, "Vector index missing for this publication. Re-ingest it.")
    result = graph.invoke({"publication_id": body.publication_id, "question": body.question, "k": body.k})
    return {"answer": result["answer"]}
