from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..db import SessionLocal
from .. import models

router = APIRouter(prefix="/analytics", tags=["analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/publications_by_category")
def get_publications_by_category(db: Session = Depends(get_db)):
    """
    Returns the count of publications for each category.
    """
    category_counts = (
        db.query(models.Category.title, func.count(models.Publication.id))
        .join(models.Publication, models.Publication.category_id == models.Category.id)
        .group_by(models.Category.title)
        .order_by(func.count(models.Publication.id).desc())
        .all()
    )
    return [{"category": c, "count": count} for c, count in category_counts]

@router.get("/basic")
def basic_analytics(db: Session = Depends(get_db)):
    # by year
    by_year = (
        db.query(models.Publication.date_year, func.count(models.Publication.id))
        .group_by(models.Publication.date_year).order_by(models.Publication.date_year.asc())
        .all()
    )
    # by organism (top 10)
    by_org = (
        db.query(models.Publication.organism, func.count(models.Publication.id))
        .group_by(models.Publication.organism)
        .order_by(func.count(models.Publication.id).desc())
        .limit(10).all()
    )
    # top tags (join p<->t)
    top_tags = (
        db.query(models.Tag.name, func.count(models.PublicationTag.publication_id))
        .join(models.PublicationTag, models.PublicationTag.tag_id == models.Tag.id)
        .group_by(models.Tag.name)
        .order_by(func.count(models.PublicationTag.publication_id).desc())
        .limit(15).all()
    )
    # by category
    category_counts = (
        db.query(models.Category.title, func.count(models.Publication.id))
        .join(models.Publication, models.Publication.category_id == models.Category.id)
        .group_by(models.Category.title)
        .order_by(func.count(models.Publication.id).desc())
        .all()
    )
    return {
        "byYear": [{"year": y if y is not None else "Unknown", "count": c} for y, c in by_year],
        "topOrganisms": [{"organism": o if o else "Unknown", "count": c} for o, c in by_org],
        "topTags": [{"tag": t, "count": c} for t, c in top_tags],
        "categories": [{"category": c, "count": count} for c, count in category_counts],
    }

@router.get("/overview")
def get_analytics_overview(db: Session = Depends(get_db)):
    pub_count = db.query(models.Publication).count()
    author_count = db.query(models.Author).count()
    tag_count = db.query(models.Tag).count()

    # Year distribution
    year_dist = db.query(models.Publication.date_year, func.count(models.Publication.id)).group_by(models.Publication.date_year).order_by(models.Publication.date_year).all()

    # Top tags
    top_tags = db.query(models.Tag.name, func.count(models.PublicationTag.publication_id).label('count')).join(models.PublicationTag).group_by(models.Tag.name).order_by(func.count(models.PublicationTag.publication_id).desc()).limit(10).all()

    return {
        "publication_count": pub_count,
        "author_count": author_count,
        "tag_count": tag_count,
        "year_distribution": {str(y): c for y, c in year_dist if y},
        "top_tags": {t: c for t, c in top_tags}
    }
