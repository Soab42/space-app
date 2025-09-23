# from __future__ import annotations

# from datetime import datetime
# from typing import Optional

# from pydantic import BaseModel, Field


# class PublicationBase(BaseModel):
#     title: str = Field(..., max_length=512)
#     abstract: Optional[str] = None


# class PublicationCreate(PublicationBase):
#     pass


# class PublicationRead(PublicationBase):
#     id: int
#     created_at: datetime

#     class Config:
#         from_attributes = True

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union

class AuthorIn(BaseModel):
    name: str
    affiliation: Optional[str] = None
    orcid: Optional[str] = None
    rank: Optional[int] = None

class PublicationIn(BaseModel):
    title: str
    abstract: Optional[str] = None
    year: Optional[int] = None
    organism: Optional[str] = None
    environment: Optional[str] = None
    original_link: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    authors: List[AuthorIn] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    # Optional: provide raw text if not uploading PDF
    text: Optional[str] = None

class PublicationOut(BaseModel):
    id: int
    title: str
    abstract: Optional[str] = None
    year: Optional[int] = None
    organism: Optional[str] = None
    environment: Optional[str] = None
    original_link: Optional[str] = None
    tags: List[str] = []
    authors: List[str] = []
    summary: Optional[str] = None
    key_findings: List[str] = []
    methods: Optional[str] = None
    conclusions: Optional[str] = None
    metadata_json: dict
    actionable_insights: Optional[List[str]] = None
    knowledge_graph: Optional[Union[str, dict]] = None

    class Config:
        from_attributes = True

class QABody(BaseModel):
    publication_id: int
    question: str
    k: int = 6
