from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union


# -------------------------
# Author
# -------------------------
class AuthorIn(BaseModel):
    name: str
    affiliation: Optional[str] = None
    orcid: Optional[str] = None
    rank: Optional[int] = None


class AuthorOut(BaseModel):
    id: int
    name: str
    affiliation: Optional[str] = None

    class Config:
        from_attributes = True


# -------------------------
# Publication
# -------------------------
class PublicationIn(BaseModel):
    title: str
    abstract: Optional[str] = None
    date_month: Optional[str] = None   # Consistent type (1-12)
    date_year: Optional[str] = None
    organism: Optional[str] = None
    environment: Optional[str] = None
    original_link: Optional[str] = None
    authors: List[AuthorIn] = Field(default_factory=list)
    category_id: Optional[int] = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    text: Optional[str] = None
    subcategory_id: Optional[int] = None
    podcast_audio_path: Optional[str] = None
    others_data: dict[str, Any] = Field(default_factory=dict)


class RelatedPublicationOut(BaseModel):
    id: int
    title: str
    date_month: Optional[int] = None
    date_year: Optional[int] = None


# -------------------------
# Tags, Categories
# -------------------------
class TagOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class CategoryOut(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True


class SubCategoryOut(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True


# -------------------------
# Knowledge / Insights
# -------------------------
# class KnowledgeGaps(BaseModel):
#     current_limitations: List[str] = []
#     research_needs: List[str] = []
#     future_directions: List[str] = []


# class ConsensusDisagreement(BaseModel):
#     scientific_consensus: List[str] = []
#     areas_of_debate: List[str] = []
#     community_perspectives: List[str] = []


class FAQ(BaseModel):
    question: str
    answer: str


# -------------------------
# Publication Out
# -------------------------
class PublicationOut(BaseModel):
    id: int
    title: str
    abstract: Optional[str] = None
    date_month: Optional[str] = None
    date_year: Optional[int] = None
    organism: Optional[str] = None
    environment: Optional[str] = None
    original_link: Optional[str] = None

    tags: List[TagOut] = []
    authors: List[AuthorOut] = []

    summary_of_abstract: Optional[str] = None
    summary_for_scientist: Optional[str] = None
    summary_for_investor: Optional[str] = None
    summary_for_mission_architect: Optional[str] = None
    podcast_audio_path: Optional[str] = None
    knowledgeable_insights: Optional[dict] = None

    perspective: Optional[List[str]] = None
    faqs: Optional[List[FAQ]] = None
    metadata_json: dict
    knowledge_graph: Optional[Union[str, dict]] = None
    others_data: dict[str, Any] = Field(default_factory=dict)

    knowledge_gaps:  dict[str, Any] = Field(default_factory=dict)
    consensus_disagreement:  dict[str, Any] = Field(default_factory=dict)
    category: Optional[CategoryOut] = None
    subcategory: Optional[SubCategoryOut] = None

    class Config:
        from_attributes = True


# -------------------------
# QA
# -------------------------
class QABody(BaseModel):
    publication_id: int
    question: str
    k: int = 6


# -------------------------
# Category / SubCategory
# -------------------------
class CategoryBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None


class CategoryCreate(CategoryBase):
    title: str


class Category(CategoryBase):
    id: int
    subcategories: List["SubCategory"] = []

    model_config = {"from_attributes": True}


class SubCategoryBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None


class SubCategoryCreate(SubCategoryBase):
    title: str
    category_id: int


class SubCategory(SubCategoryBase):
    id: int
    category_id: int

    model_config = {"from_attributes": True}


# -------------------------
# Resolve forward refs
# -------------------------
Category.model_rebuild()
SubCategory.model_rebuild()
