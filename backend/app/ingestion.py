import os, io
from typing import List
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from sqlalchemy.orm import Session
from .models import Publication, Author, PublicationAuthor, Tag, PublicationTag
from .vectorstore import save_faiss_for_publication, upsert_global_documents
from .config import get_settings
from .rag_graph import generate_section_summaries, _llm
from .knowledge_graph import extract_knowledge_graph
from pydantic import BaseModel, Field
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from fastapi.encoders import jsonable_encoder
class InsightsList(BaseModel):
    insights: List[str]

def extract_actionable_insights(text: str) -> List[str]:
    """
    Extracts actionable insights from a given text using an LLM.
    """
    llm = _llm()
    parser = PydanticOutputParser(pydantic_object=InsightsList)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert at extracting actionable insights, recommendations, and countermeasures for mission planners from scientific papers. "
                "Extract a list of such insights from the provided text. Focus on concrete actions, not general findings."
                "Return ONLY valid JSON that conforms exactly to the schema and format instructions."
            ),
            (
                "user",
                "Text:\n{text}\n\nFORMAT INSTRUCTIONS:\n{format_instructions}"
            ),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser

    try:
        # Limit the text size to avoid exceeding token limits
        truncated_text = text[:12000]
        extracted = chain.invoke({"text": truncated_text})
        return extracted.insights
    except Exception as e:
        print(f"Error extracting actionable insights: {e}")
        return []

from concurrent.futures import ThreadPoolExecutor

settings = get_settings()

def _pdf_to_text(path: str) -> str:
    reader = PdfReader(path)
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
    return "\n".join(parts).strip()

def chunk_text(text: str) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    chunks = splitter.split_text(text)
    return [Document(page_content=c, metadata={}) for c in chunks]

def upsert_authors(db: Session, publication_id: int, authors_in: list[dict]):
    from .models import Author, PublicationAuthor
    for idx, a in enumerate(authors_in):
        name = (a.get("name") or "").strip()
        if not name:
            continue
        aff = a.get("affiliation")
        orcid = a.get("orcid")
        author = db.query(Author).filter(Author.name == name, Author.orcid == orcid).first()
        if not author:
            author = Author(name=name, affiliation=aff, orcid=orcid)
            db.add(author); db.flush()
        link = db.query(PublicationAuthor).filter_by(publication_id=publication_id, author_id=author.id).first()
        if not link:
            db.add(PublicationAuthor(publication_id=publication_id, author_id=author.id, rank=a.get("rank", idx+1)))

def upsert_tags(db: Session, publication_id: int, tags: list[str]):
    from .models import Tag, PublicationTag
    for t in tags:
        tagname = (t or "").strip().lower()
        if not tagname:
            continue
        tag = db.query(Tag).filter(Tag.name == tagname).first()
        if not tag:
            tag = Tag(name=tagname)
            db.add(tag); db.flush()
        link = db.query(PublicationTag).filter_by(publication_id=publication_id, tag_id=tag.id).first()
        if not link:
            db.add(PublicationTag(publication_id=publication_id, tag_id=tag.id))

# def ingest_publication(db: Session, pub: Publication, text: str) -> None:
#     # 1) Chunk
#     docs = chunk_text(text)
#     for i, d in enumerate(docs):
#         d.metadata.update({
#             "publication_id": pub.id,
#             "title": pub.title,
#             "chunk_id": i+1,
#             "year": pub.year,
#             "organism": pub.organism,
#             "environment": pub.environment,
#             "type": "publication_chunk"
#         })
#         print('docs', docs)
#     # 2) Per-publication FAISS
#     save_faiss_for_publication(pub.id, docs)

#     # 3) Global FAISS (adds/updates)
#     upsert_global_documents(docs)


def ingest_publication(db: Session, pub: Publication, text: str) -> None:
    print(f"Ingesting publication {pub.id}...")
    
    # Generate AI sectioned summaries
    sections = generate_section_summaries(pub.title, text, pub.abstract)
    print("sections", sections.model_dump())  # debugging

    # Summaries
    pub.summary_of_abstract = sections.abstract_summary
    pub.summary_for_scientist = sections.scientist_summary
    pub.summary_for_investor = sections.investor_summary
    pub.summary_for_mission_architect = sections.mission_architect_summary

    # Knowledge graph (JSON-serializable)
    pub.knowledge_graph = jsonable_encoder(sections.knowledge_graph)

    # Actionable insights
    pub.knowledgeable_insights = jsonable_encoder(sections.scientific_progress)

    # Knowledge gaps, consensus, FAQs
    pub.knowledge_gaps = jsonable_encoder(sections.knowledge_gaps)
    pub.consensus_disagreement = jsonable_encoder(sections.consensus)
    pub.faqs = jsonable_encoder(sections.faqs)

    # Tags
    upsert_tags(db, pub.id, sections.tags)

    db.add(pub)
    db.commit()
    print(f"AI summaries completed for publication {pub.id}.")

    # -------------------------------
    # 1️⃣ Chunk and add metadata
    docs = chunk_text(text)
    for i, d in enumerate(docs):
        d.metadata.update({
            "publication_id": pub.id,
            "title": pub.title,
            "chunk_id": i+1,
            "year": pub.date_year,
            "organism": pub.organism,
            "environment": pub.environment,
            "type": "publication_chunk"
        })
    print("Docs prepared with metadata.")

    # -------------------------------
    # 2️⃣ Save per-publication FAISS
    save_faiss_for_publication(pub.id, docs)
    print("Per-publication FAISS saved.")

    # -------------------------------
    # 3️⃣ Update global FAISS
    upsert_global_documents(docs)
    print("Global FAISS updated.")

