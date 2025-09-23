
from pydantic import BaseModel, Field
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from .rag_graph import _llm

class Node(BaseModel):
    id: str = Field(..., description="Unique identifier for the node (e.g., 'Perseverance').")
    type: str = Field(..., description="Type of the entity (e.g., 'Rover').")

class Edge(BaseModel):
    source: str = Field(..., description="ID of the source node.")
    target: str = Field(..., description="ID of the target node.")
    relation: str = Field(..., description="Description of the relationship (e.g., 'landed_on').")

class KnowledgeGraph(BaseModel):
    nodes: List[Node]
    edges: List[Edge]

def extract_knowledge_graph(text: str) -> KnowledgeGraph:
    """
    Extracts a knowledge graph from a given text.
    """
    llm = _llm()
    parser = PydanticOutputParser(pydantic_object=KnowledgeGraph)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert at extracting knowledge graphs from scientific text. "
                "Extract entities and relationships from the provided text and return them in JSON format."
                "Return ONLY valid JSON that conforms exactly to the schema and format instructions."
            ),
            (
                "user",
                "Text:\n{text}\n\nFORMAT INSTRUCTIONS:\n{format_instructions}"
            ),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser
    
    # Limit the text size to avoid exceeding token limits
    truncated_text = text[:12000]
    
    return chain.invoke({"text": truncated_text})

