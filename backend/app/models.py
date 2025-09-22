# from __future__ import annotations

# from datetime import datetime

# from sqlalchemy import Integer, String, Text, DateTime
# from sqlalchemy.orm import Mapped, mapped_column

# from .db import Base


# class Publication(Base):
#     __tablename__ = "publications"

#     id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
#     title: Mapped[str] = mapped_column(String(512), nullable=False)
#     abstract: Mapped[str] = mapped_column(Text, nullable=True)
#     created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from .db import Base

class Publication(Base):
    __tablename__ = "publications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    organism: Mapped[str | None] = mapped_column(String(128))
    environment: Mapped[str | None] = mapped_column(String(128))  # e.g., microgravity, ISS, lunar, Mars
    original_link: Mapped[str | None] = mapped_column(String(1024))
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default={})
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # AI-generated fields
    summary: Mapped[str | None] = mapped_column(Text)
    key_findings: Mapped[str | None] = mapped_column(Text)
    methods: Mapped[str | None] = mapped_column(Text)
    conclusions: Mapped[str | None] = mapped_column(Text)

    authors: Mapped[list["Author"]] = relationship(
        "Author", secondary="publication_authors", back_populates="publications"
    )
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary="publication_tags", back_populates="publications"
    )

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
