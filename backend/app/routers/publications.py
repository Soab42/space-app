
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import cast, Integer
from typing import List
import json, os, shutil
from ..db import SessionLocal
from .. import models, schemas
from ..ingestion import ingest_publication, _pdf_to_text, upsert_authors, upsert_tags
from ..config import get_settings
from pydantic import BaseModel

router = APIRouter(prefix="/publications", tags=["publications"])
settings = get_settings()

class PaginatedPublicationOut(BaseModel):
    total: int
    publications: List[schemas.PublicationOut]

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

@router.get("", response_model=PaginatedPublicationOut)
def list_publications(q: str | None = None, year_from: int | None = None, year_to: int | None = None, organism: str | None = None, category_id: int | None = None, subcategory_id: int | None = None, start_date: str | None = None, end_date: str | None = None, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    query = db.query(models.Publication)
    if q:
        like = f"%{q}%"
        query = query.filter(models.Publication.title.ilike(like) | models.Publication.abstract.ilike(like))
    if year_from:
        query = query.filter(cast(models.Publication.date_year, Integer) >= year_from)
    if year_to:
        query = query.filter(cast(models.Publication.date_year, Integer) <= year_to)
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
    
    total_publications = query.count()
    pubs = query.order_by(models.Publication.created_at.desc()).offset(skip).limit(limit).all()
    
    return {"total": total_publications, "publications": [schemas.PublicationOut.from_orm(p) for p in pubs]}

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


@router.put("/{publication_id}", response_model=schemas.PublicationOut)
def update_publication(
    publication_id: int,
    publication_update: schemas.PublicationUpdate,
    db: Session = Depends(get_db)
):
    publication = db.get(models.Publication, publication_id)
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")

    update_data = publication_update.model_dump(exclude_unset=True)

    if "add_more_context" in update_data and update_data["add_more_context"]:
        from ..vectorstore import add_context_to_publication
        add_context_to_publication(publication_id, update_data["add_more_context"])
        del update_data["add_more_context"] # remove it from the publication update data

    for key, value in update_data.items():
        if key == "authors":
            upsert_authors(db, publication_id, value)
        elif key == "tags":
            upsert_tags(db, publication_id, value)
        else:
            setattr(publication, key, value)

    db.commit()
    db.refresh(publication)

    return schemas.PublicationOut.from_orm(publication)


@router.get("/{pub_id}/related", response_model=List[schemas.PublicationOut])
def get_related_publications(pub_id: int, db: Session = Depends(get_db)):
    # Get the original publication to find its tags
    original_publication = db.get(models.Publication, pub_id)
    if not original_publication:
        raise HTTPException(status_code=404, detail="Publication not found")

    # Extract tag IDs from the original publication
    original_tag_ids = {tag.id for tag in original_publication.tags}
    if not original_tag_ids:
        return []

    # Find publications that share at least one tag with the original publication
    # Use a subquery to get distinct publication IDs first, to avoid distinct on JSON columns
    subquery = (
        db.query(models.Publication.id)
        .join(models.Publication.tags)
        .filter(models.Tag.id.in_(original_tag_ids))
        .filter(models.Publication.id != pub_id)
        .distinct()
    )
    related_publications = (
        db.query(models.Publication)
        .filter(models.Publication.id.in_(subquery))
        .limit(5)
        .all()
    )
    
    return [schemas.PublicationOut.from_orm(p) for p in related_publications]

