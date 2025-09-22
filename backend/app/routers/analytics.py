from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..db import SessionLocal
from ..models import Publication, Tag, PublicationTag

router = APIRouter(prefix="/analytics", tags=["analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/basic")
def basic_analytics(db: Session = Depends(get_db)):
    # by year
    by_year = (
        db.query(Publication.year, func.count(Publication.id))
        .group_by(Publication.year).order_by(Publication.year.asc())
        .all()
    )
    # by organism (top 10)
    by_org = (
        db.query(Publication.organism, func.count(Publication.id))
        .group_by(Publication.organism)
        .order_by(func.count(Publication.id).desc())
        .limit(10).all()
    )
    # top tags (join p<->t)
    top_tags = (
        db.query(Tag.name, func.count(PublicationTag.publication_id))
        .join(PublicationTag, PublicationTag.tag_id == Tag.id)
        .group_by(Tag.name)
        .order_by(func.count(PublicationTag.publication_id).desc())
        .limit(15).all()
    )
    return {
        "byYear": [{"year": y if y is not None else "Unknown", "count": c} for y, c in by_year],
        "topOrganisms": [{"organism": o if o else "Unknown", "count": c} for o, c in by_org],
        "topTags": [{"tag": t, "count": c} for t, c in top_tags],
    }
