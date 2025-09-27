from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from .db import Base

class Publication(Base):
    __tablename__ = "publications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_month: Mapped[str | None] = mapped_column(String(128), index=True)
    date_year: Mapped[str | None] = mapped_column(String(128), index=True)
    organism: Mapped[str | None] = mapped_column(String(128))
    environment: Mapped[str | None] = mapped_column(String(128))  # e.g., microgravity, ISS, lunar, Mars
    original_link: Mapped[str | None] = mapped_column(String(1024))
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default={})
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # AI-generated fields
    summary_of_abstract: Mapped[str | None] = mapped_column(Text)
    summary_for_scientist: Mapped[str | None] = mapped_column(Text)
    summary_for_investor: Mapped[str | None] = mapped_column(Text)
    summary_for_mission_architect: Mapped[str | None] = mapped_column(Text)
    podcast_audio_path: Mapped[str | None] = mapped_column(String(1024))
    knowledgeable_insights: Mapped[dict | None] = mapped_column(JSON, default={})
    knowledge_gaps: Mapped[dict | None] = mapped_column(JSON, default={})
    consensus_disagreement: Mapped[dict | None] = mapped_column(JSON, default={})
    perspective: Mapped[list | None] = mapped_column(JSON, default=[])
    faqs: Mapped[list | None] = mapped_column(JSON, default=[])
    key_findings: Mapped[list | None] = mapped_column(JSON, default=[])
    methods: Mapped[str | None] = mapped_column(Text)
    knowledge_graph: Mapped[dict | None] = mapped_column(JSON, default={})
    authors: Mapped[list["Author"]] = relationship(
        "Author", secondary="publication_authors", back_populates="publications"
    )
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary="publication_tags", back_populates="publications"
    )
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship("Category", back_populates="publications")
    subcategory_id = Column(Integer, ForeignKey('subcategories.id'))
    subcategory = relationship("SubCategory", back_populates="publications")
    others_data: Mapped[dict | None] = mapped_column(JSON, default={})


class Author(Base):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    affiliation: Mapped[str | None] = mapped_column(String(256))
    orcid: Mapped[str | None] = mapped_column(String(64), index=True)
    publications: Mapped[list[Publication]] = relationship(
        "Publication", secondary="publication_authors", back_populates="authors"
    )

class PublicationAuthor(Base):
    __tablename__ = "publication_authors"
    publication_id: Mapped[int] = mapped_column(ForeignKey("publications.id"), primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), primary_key=True)
    rank: Mapped[int | None] = mapped_column(Integer)  # author order

class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    publications: Mapped[list[Publication]] = relationship(
        "Publication", secondary="publication_tags", back_populates="tags"
    )

class PublicationTag(Base):
    __tablename__ = "publication_tags"
    publication_id: Mapped[int] = mapped_column(ForeignKey("publications.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    image = Column(String, nullable=True)

    # ✅ Add this to fix error
    publications: Mapped[list["Publication"]] = relationship(
        "Publication", back_populates="category"
    )

    subcategories: Mapped[list["SubCategory"]] = relationship(
        "SubCategory", back_populates="category"
    )

class SubCategory(Base):
    __tablename__ = 'subcategories'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    image = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey('categories.id'))
    # ✅ Add this to fix error
    category: Mapped["Category"] = relationship("Category", back_populates="subcategories")

    publications: Mapped[list["Publication"]] = relationship(
        "Publication", back_populates="subcategory"
    )

