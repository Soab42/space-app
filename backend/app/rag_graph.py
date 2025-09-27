
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List,TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain.schema import Document
from .config import get_settings
from .vectorstore import load_faiss_for_publication
from langchain.output_parsers import PydanticOutputParser


settings = get_settings()
print('settings', settings)

def _llm():
    if settings.LLM_PROVIDER == "openai":
        return ChatOpenAI(model=settings.LLM_MODEL, api_key=settings.OPENAI_API_KEY, temperature=0)
    elif settings.LLM_PROVIDER == "ollama":
        return ChatOllama(model=settings.LLM_MODEL, temperature=0)
    else:
        raise ValueError("Unsupported LLM_PROVIDER")

class QAState(TypedDict):
    publication_id: int
    question: str
    k: int
    docs: List[Document]
    answer: str

# ---------- Schema ----------
class KnowledgeGraph(BaseModel):
    nodes: List[dict] = Field(..., description="List of nodes in the knowledge graph")
    edges: List[dict] = Field(..., description="List of edges connecting the nodes")

class ScientificProgress(BaseModel):
    recent_advances: List[str] = Field(..., description="List of recent advances in the field")
    key_breakthroughs: List[str] = Field(..., description="Key scientific breakthroughs")
    impact_on_field: List[str] = Field(..., description="Impact on the scientific field")

class KnowledgeGaps(BaseModel):
    current_limitations: List[str] = Field(..., description="Current limitations in the research")
    research_needs: List[str] = Field(..., description="Identified research needs")
    future_directions: List[str] = Field(..., description="Suggested future research directions")

class Consensus(BaseModel):
    scientific_consensus: List[str] = Field(..., description="Areas of scientific consensus")
    areas_of_debate: List[str] = Field(..., description="Areas where there is ongoing debate")
    community_perspectives: List[str] = Field(..., description="Diverse community perspectives")

class FAQ(BaseModel):
    question: str = Field(..., description="Frequently asked question")
    answer: str = Field(..., description="Answer to the question")

class SectionSummaries(BaseModel):
    abstract_summary: str = Field(..., description="Concise summary of the abstract (not full abstract)")
    scientist_summary: str = Field(..., description="Summary for scientists (max 70 words)")
    investor_summary: str = Field(..., description="Summary for investors (max 70 words)")
    mission_architect_summary: str = Field(..., description="Summary for mission architects (max 70 words)")
    knowledge_graph: KnowledgeGraph = Field(..., description="Structured knowledge graph with nodes and edges")
    scientific_progress: Optional[ScientificProgress] = Field(None, description="Scientific progress insights")
    knowledge_gaps: Optional[KnowledgeGaps] = Field(None, description="Identified knowledge gaps")
    consensus: Optional[Consensus] = Field(None, description="Scientific consensus and debates")
    faqs: List[FAQ] = Field(..., description="List of frequently asked questions and answers")
    tags: List[str] = Field(..., description="List of tags or keywords that summarize the paper and connect related papers using this tags")



def retrieve(state: QAState) -> QAState:
    vs = load_faiss_for_publication(state["publication_id"])
    docs = vs.similarity_search(state["question"], k=state["k"])
    state["docs"] = docs
    print('docs', docs)
    return state

def generate(state: QAState) -> QAState:
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are an assistant for Q&A on a single NASA bioscience publication. "
         "Answer **only** from the provided context. If unsure, say you don't know. "
         "Return citations as [chunk #]."),
        ("human", "Question: {question}\n\nContext:\n{context}\n\nAnswer:")
    ])
    ctx = []
    for i, d in enumerate(state["docs"], start=1):
        ctx.append(f"[{i}] {d.page_content[:1200]}")
    chain = prompt | _llm()
    out = chain.invoke({"question": state["question"], "context": "\n\n".join(ctx)})
    state["answer"] = out.content
    print('answer', state["answer"])
    return state

def build_qa_graph():
    g = StateGraph(QAState)
    # add nodes
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)

    # add edges
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    print('graph', g)
    return g.compile()

# Simple LLM call for summaries on ingestion
# def generate_section_summaries(title: str, full_text: str) -> dict:
#     llm = _llm()
#     sys = ("Summarize the following scientific paper into concise sections:\n"
#            f"Title: {title}\n"
#            "Write 4 parts:\n"
#            "1) OVERALL (3-5 sentences),\n"
#            "2) KEY_FINDINGS (bulleted),\n"
#            "3) METHODS (2-4 sentences),\n"
#            "4) CONCLUSIONS (2-3 sentences).\n"
#            "Keep it factual and faithful; do not invent details.")
#     msg = llm.invoke([("system", sys), ("user", full_text[:120000])])
#     # Simple parse (robust enough for MVP)
#     text = msg.content
#     def take(label):  # naive split
#         import re
#         m = re.search(label+r".*?:\s*(.*?)(?:\n[A-Z_]+\s*:|$)", text, re.S)
#         return m.group(1).strip() if m else None
#     return {
#         "overall": take(r"OVERALL"),
#         "key_findings": take(r"KEY_FINDINGS"),
#         "methods": take(r"METHODS"),
#         "conclusions": take(r"CONCLUSIONS")
#     }
# ---------- Main function ----------
def generate_section_summaries(title: str, full_text: str, abstract: str) -> SectionSummaries:
    llm = _llm()
    parser = PydanticOutputParser(pydantic_object=SectionSummaries)

    # Build prompt with parser's format instructions (enforces JSON shape)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a precise assistant for scientific summarization. "
                "Return ONLY valid JSON that conforms exactly to the schema and format instructions.\n"
                "For the knowledge graph, identify key entities (people, places, concepts, technologies) "
                "as nodes and their relationships as edges.\n"
                "For the FAQ section, generate 3-5 common questions and answers that a reader might have.",
            ),
            (
                "user",
                (
                    f"Title: {title}\n\n"
                    "Abstract: {abstract}\n\n"
                    "Please analyze this scientific paper and provide the following structured information:\n\n"
                    "1. A concise summary of the abstract (not the full abstract)\n"
                    "2. A summary for scientists (max 70 words)\n"
                    "3. A summary for investors (max 70 words)\n"
                    "4. A summary for mission architects (max 70 words)\n"
                    "5. A knowledge graph with nodes (entities) and edges (relationships)\n"
                    "6. Scientific progress insights (recent advances, key breakthroughs, impact on field)\n"
                    "7. Knowledge gaps (current limitations, research needs, future directions)\n"
                    "8. Consensus and debates (scientific consensus, areas of debate, community perspectives)\n"
                    "9. 3-5 frequently asked questions with answers\n"
                    "10. Give a list of tags or keywords that summarize the paper\n\n"
                    "Paper Content (truncated if long):\n"
                    "{content}\n\n"
                    "IMPORTANT: Return ONLY valid JSON that matches the schema exactly.\n"
                    "FORMAT INSTRUCTIONS:\n{format_instructions}"
                ),
            ),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    # Run the chain: prompt -> LLM -> parse
    content = full_text[:120000] if full_text else ""
    msg = llm.invoke(prompt.format_messages(content=content, abstract=abstract))
    try:
        print('output from llm ', msg.content)
        return parser.parse(msg.content)
    except ValidationError as ve:
        # If the model drifts, give one best-effort repair attempt by asking Mistral to fix to schema
        repair_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "Fix the JSON to match the schema exactly. Return ONLY valid JSON."),
                ("user", f"JSON to fix:\n{msg.content}\n\n{parser.get_format_instructions()}"),
            ]
        )
        repaired = llm.invoke(repair_prompt.format_messages())
        return parser.parse(repaired.content)