
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json, os, shutil
from ..db import SessionLocal
from .. import models, schemas
from ..ingestion import ingest_publication, _pdf_to_text, upsert_authors, upsert_tags
from ..config import get_settings

router = APIRouter(prefix="/publications", tags=["publications"])
settings = get_settings()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("", response_model=schemas.PublicationOut)
async def create_publication(
    metadata_json: str = Form(...), 
    pdf: UploadFile | None = File(default=None)
    , db: Session = Depends(get_db)):
    try:
        meta = json.loads(metadata_json)
        pub_in = schemas.PublicationIn(**meta)
    except Exception as e:
        raise HTTPException(400, f"Invalid metadata_json: {e}")

    pub = models.Publication(
        title=pub_in.title,
        abstract=pub_in.abstract,
        year=pub_in.year,
        organism=pub_in.organism,
        environment=pub_in.environment,
        original_link=pub_in.original_link,
        metadata_json=pub_in.metadata_json or {}
    )
    db.add(pub); db.flush()

    # Authors & tags (before ingest to ensure relationships)
    upsert_authors(db, pub.id, [a.model_dump() for a in pub_in.authors])
    upsert_tags(db, pub.id, pub_in.tags)
    db.commit(); db.refresh(pub)

    # Prepare text
    if pub_in.text:
        text = pub_in.text
    elif pdf is not None:
        save_path = os.path.join(settings.UPLOADS_DIR, f"pub_{pub.id}_{pdf.filename}")
        with open(save_path, "wb") as f:
            shutil.copyfileobj(pdf.file, f)
        text = _pdf_to_text(save_path)
    else:
        raise HTTPException(400, "Provide either metadata_json.text or a PDF file.")

    if not text.strip():
        raise HTTPException(400, "No text extracted from PDF / provided.")

    # Ingest (vectorize + summarize)
    db = SessionLocal()
    
    pub = db.get(models.Publication, pub.id)
    ingest_publication(db, pub, text)
    db.commit(); db.refresh(pub)

    # Build output
    return schemas.PublicationOut(
        id=pub.id,
        title=pub.title,
        abstract=pub.abstract,
        year=pub.year,
        organism=pub.organism,
        environment=pub.environment,
        original_link=pub.original_link,
        tags=[t.name for t in pub.tags],
        authors=[a.name for a in pub.authors],
        summary=pub.summary,
        key_findings=json.loads(pub.key_findings) if pub.key_findings else [],
        methods=pub.methods,
        conclusions=pub.conclusions,
        metadata_json=pub.metadata_json or {}
    )

@router.get("", response_model=List[schemas.PublicationOut])
def list_publications(q: str | None = None, year: int | None = None, organism: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Publication)
    if q:
        like = f"%{q}%"
        query = query.filter(models.Publication.title.ilike(like) | models.Publication.abstract.ilike(like))
    if year:
        query = query.filter(models.Publication.year == year)
    if organism:
        query = query.filter(models.Publication.organism.ilike(f"%{organism}%"))
    pubs = query.order_by(models.Publication.created_at.desc()).limit(200).all()
    out = []
    for p in pubs:
        out.append(schemas.PublicationOut(
            id=p.id, title=p.title, abstract=p.abstract, year=p.year, organism=p.organism,
            environment=p.environment, original_link=p.original_link, tags=[t.name for t in p.tags],
            authors=[a.name for a in p.authors], summary=p.summary, key_findings = json.loads(p.key_findings) if p.key_findings else [],
            methods=p.methods, conclusions=p.conclusions, metadata_json=p.metadata_json or {}
        ))
    return out

@router.get("/{pub_id}", response_model=schemas.PublicationOut)
def get_publication(pub_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Publication, pub_id)
    if not p:
        raise HTTPException(404, "Publication not found")

    return schemas.PublicationOut(
        id=p.id,
        title=p.title,
        abstract=p.abstract,
        year=p.year,
        organism=p.organism,
        environment=p.environment,
        original_link=p.original_link,
        tags=[t.name for t in p.tags],
        authors=[a.name for a in p.authors],
        summary=p.summary,
        key_findings = json.loads(p.key_findings) if p.key_findings else [],
        methods=p.methods,
        conclusions=p.conclusions,
        metadata_json=p.metadata_json or {},
        actionable_insights=p.actionable_insights,
        knowledge_graph=p.knowledge_graph,
    )
