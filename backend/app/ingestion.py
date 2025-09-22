import os, io
from typing import List
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from sqlalchemy.orm import Session
from .models import Publication, Author, PublicationAuthor, Tag, PublicationTag
from .vectorstore import save_faiss_for_publication, upsert_global_documents
from .config import get_settings
from .rag_graph import generate_section_summaries
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
    # -------------------------------
    print(f"Ingesting publication {pub.id}...")

    # AI sectioned summaries
    sections = generate_section_summaries(pub.title, text)
    print("sections", sections.model_dump())  # for debugging

    pub.summary = sections.overall
    pub.key_findings = sections.key_findings
    pub.methods = sections.methods
    pub.conclusions = sections.conclusions

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
            "year": pub.year,
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

    # -------------------------------
    # 4️⃣ Generate AI sectioned summaries (parallelized)
    def generate_and_save_summaries():
        sections = generate_section_summaries(pub.title, text)
        pub.summary = sections.get("overall")
        pub.key_findings = sections.get("key_findings")
        pub.methods = sections.get("methods")
        pub.conclusions = sections.get("conclusions")
        db.add(pub)
        db.commit()
        print(f"AI summaries completed for publication {pub.id}.")

