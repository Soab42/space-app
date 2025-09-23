
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import SessionLocal
from .. import models

router = APIRouter(prefix="/graph", tags=["graph"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{pub_id}")
def get_knowledge_graph(pub_id: int, db: Session = Depends(get_db)):
    pub = db.get(models.Publication, pub_id)
    if not pub:
        raise HTTPException(404, "Publication not found")
    return pub.knowledge_graph
