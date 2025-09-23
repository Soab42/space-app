from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import Counter
from ..db import SessionLocal
from .. import models
from ..rag_graph import _llm
from pydantic import BaseModel, Field
from typing import List

class ActionableInsight(BaseModel):
    publication_id: int
    insight: str = Field(..., description="A single, actionable insight, recommendation, or countermeasure.")

from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

class Comparison(BaseModel):
    methodology_comparison: str = Field(..., description="Comparison of the methodologies of the two papers.")
    results_comparison: str = Field(..., description="Comparison of the results of the two papers.")
    conclusions_comparison: str = Field(..., description="Comparison of the conclusions of the two papers.")


router = APIRouter(prefix="/analytics", tags=["analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/overview")
def get_analytics_overview(db: Session = Depends(get_db)):
    pub_count = db.query(models.Publication).count()
    author_count = db.query(models.Author).count()
    tag_count = db.query(models.Tag).count()

    # Year distribution
    year_dist = db.query(models.Publication.year, func.count(models.Publication.id)).group_by(models.Publication.year).order_by(models.Publication.year).all()

    # Top tags
    top_tags = db.query(models.Tag.name, func.count(models.PublicationTag.publication_id).label('count')).join(models.PublicationTag).group_by(models.Tag.name).order_by(func.count(models.PublicationTag.publication_id).desc()).limit(10).all()

    return {
        "publication_count": pub_count,
        "author_count": author_count,
        "tag_count": tag_count,
        "year_distribution": {str(y): c for y, c in year_dist if y},
        "top_tags": {t: c for t, c in top_tags}
    }

@router.get("/compare", response_model=Comparison)
def compare_publications(ids: str, db: Session = Depends(get_db)):
    """
    Compares two publications side-by-side.
    """
    try:
        pub_ids = [int(id) for id in ids.split(",")]
        if len(pub_ids) != 2:
            raise HTTPException(400, "Please provide exactly two publication IDs to compare.")
    except ValueError:
        raise HTTPException(400, "Invalid publication IDs provided.")

    pubs = db.query(models.Publication).filter(models.Publication.id.in_(pub_ids)).all()
    if len(pubs) != 2:
        raise HTTPException(404, "One or both publications not found.")

    # Prepare text for LLM
    text1 = f"Title: {pubs[0].title}\nAbstract: {pubs[0].abstract}\nKey Findings: {pubs[0].key_findings}\nMethods: {pubs[0].methods}\nConclusions: {pubs[0].conclusions}"
    text2 = f"Title: {pubs[1].title}\nAbstract: {pubs[1].abstract}\nKey Findings: {pubs[1].key_findings}\nMethods: {pubs[1].methods}\nConclusions: {pubs[1].conclusions}"

    llm = _llm()
    parser = PydanticOutputParser(pydantic_object=Comparison)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert at comparing two scientific papers. Provide a detailed comparison of their methodologies, results, and conclusions."
                "Return ONLY valid JSON that conforms exactly to the schema and format instructions."
            ),
            (
                "user",
                "Paper 1:\n{text1}\n\nPaper 2:\n{text2}\n\nFORMAT INSTRUCTIONS:\n{format_instructions}"
            ),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser
    
    return chain.invoke({"text1": text1, "text2": text2})

@router.get("/program_manager_dashboard")
def get_program_manager_dashboard(db: Session = Depends(get_db)):
    """
    Provides a high-level overview for program managers.
    """
    overview = get_analytics_overview(db)

    # Distribution by environment
    env_dist = db.query(models.Publication.environment, func.count(models.Publication.id)).group_by(models.Publication.environment).all()

    # Distribution by organism
    org_dist = db.query(models.Publication.organism, func.count(models.Publication.id)).group_by(models.Publication.organism).all()

    return {
        "overview": overview,
        "environment_distribution": {env: count for env, count in env_dist if env},
        "organism_distribution": {org: count for org, count in org_dist if org}
    }

@router.get("/mission_planner_dashboard", response_model=List[ActionableInsight])
def get_mission_planner_dashboard(db: Session = Depends(get_db)):
    """
    Retrieves pre-calculated actionable insights for mission planners.
    """
    all_pubs = db.query(models.Publication).filter(models.Publication.actionable_insights != None).all()

    insights = []
    for pub in all_pubs:
        if pub.actionable_insights:
            for insight_text in pub.actionable_insights:
                insights.append(ActionableInsight(publication_id=pub.id, insight=insight_text))
    
    return insights


@router.get("/consensus_and_gaps")
def get_consensus_and_gaps(db: Session = Depends(get_db)):
    """
    Analyzes all publications to find consensus, disagreements, and knowledge gaps.
    """
    publications = db.query(models.Publication).all()
    
    # 1. Knowledge Gaps from Tags
    all_tags = db.query(models.Tag.name, func.count(models.PublicationTag.publication_id).label('count')).join(models.PublicationTag, isouter=True).group_by(models.Tag.name).all()
    tag_counts = {tag: count for tag, count in all_tags}
    
    # Simple heuristic for gaps: tags with few publications
    knowledge_gaps = {tag: count for tag, count in tag_counts.items() if count <= 2} # Arbitrary threshold

    # 2. Consensus from Key Findings
    all_findings = []
    for pub in publications:
        if pub.key_findings:
            # Assuming key_findings is a list of strings
            all_findings.extend(pub.key_findings)

    # Simple consensus: most common findings
    consensus = dict(Counter(all_findings).most_common(10))

    return {
        "consensus": consensus,
        "knowledge_gaps": knowledge_gaps,
        "tag_distribution": tag_counts
    }

@router.get("/basic")
def basic_analytics(db: Session = Depends(get_db)):
    # by year
    by_year = (
        db.query(models.Publication.year, func.count(models.Publication.id))
        .group_by(models.Publication.year).order_by(models.Publication.year.asc())
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
    return {
        "byYear": [{"year": y if y is not None else "Unknown", "count": c} for y, c in by_year],
        "topOrganisms": [{"organism": o if o else "Unknown", "count": c} for o, c in by_org],
        "topTags": [{"tag": t, "count": c} for t, c in top_tags],
    }
