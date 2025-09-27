
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
    pdf: UploadFile | None = File(default=None),
    db: Session = Depends(get_db)):
    try:
        meta = json.loads(metadata_json)
        pub_in = schemas.PublicationIn(**meta)
    except Exception as e:
        raise HTTPException(400, f"Invalid metadata_json: {e}")
    # print(pub_in)
    # return
    pub = models.Publication(
        title=pub_in.title,
        abstract=pub_in.abstract,
        date_year=pub_in.date_year,
        date_month=pub_in.date_month,
        organism=pub_in.organism,
        environment=pub_in.environment,
        original_link=pub_in.original_link,
        metadata_json=pub_in.metadata_json or {},
        category_id=pub_in.category_id,
        subcategory_id=pub_in.subcategory_id,
        podcast_audio_path=pub_in.podcast_audio_path,
        others_data=pub_in.others_data
    )
    db.add(pub)
    db.commit()
    db.refresh(pub)

    # Authors & tags (before ingest to ensure relationships)
    upsert_authors(db, pub.id, [a.model_dump() for a in pub_in.authors])
    # upsert_tags(db, pub.id, pub_in.tags)
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
    # print('pub', pub_in)
    # print('abstract', pub_in.abstract)
    ingest_publication(db, pub, text)
    db.commit(); db.refresh(pub)

    # format authors
    # pub.authors = [schemas.AuthorOut(**a.model_dump()) for a in pub.authors]
    # pub.tags = [schemas.TagOut(**t.model_dump()) for t in pub.tags]

    # Build output
    return schemas.PublicationOut.from_orm(pub)

@router.get("", response_model=List[schemas.PublicationOut])
def list_publications(q: str | None = None, year_from: int | None = None, year_to: int | None = None, organism: str | None = None, category_id: int | None = None, subcategory_id: int | None = None, start_date: str | None = None, end_date: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Publication)
    if q:
        like = f"%{q}%"
        query = query.filter(models.Publication.title.ilike(like) | models.Publication.abstract.ilike(like))
    if year_from:
        query = query.filter(models.Publication.date_year >= year_from)
    if year_to:
        query = query.filter(models.Publication.date_year <= year_to)
    if organism:
        query = query.filter(models.Publication.organism.ilike(f"%{organism}%"))
    if category_id:
        query = query.filter(models.Publication.category_id==category_id)
    if subcategory_id:
        query = query.filter(models.Publication.subcategory_id == subcategory_id)
    if start_date:
        query = query.filter(models.Publication.created_at >= start_date)
    if end_date:
        query = query.filter(models.Publication.created_at <= end_date)
    pubs = query.order_by(models.Publication.created_at.desc()).limit(200).all()
    
    return [schemas.PublicationOut.from_orm(p) for p in pubs]

@router.get("/{pub_id}", response_model=schemas.PublicationOut)
def get_publication(pub_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Publication, pub_id)
    if not p:
        raise HTTPException(status_code=404, detail="Publication not found")
    
    pub_out = schemas.PublicationOut.from_orm(p)

    # If empty list/dict → set to None
    if not pub_out.knowledge_gaps:  # catches [], {}, or None
        pub_out.knowledge_gaps = None

    if not pub_out.consensus_disagreement:
        pub_out.consensus_disagreement = None

    return pub_out

