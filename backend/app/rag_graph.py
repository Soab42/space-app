
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
class SectionSummaries(BaseModel):
    overall: str = Field(..., description="3-5 sentence overview of the paper.")
    key_findings: List[str] = Field(
        ..., description="Short bullet-style findings, each a concise string."
    )
    methods: str = Field(..., description="2-4 sentence description of methods.")
    conclusions: str = Field(..., description="2-3 sentence conclusions.")



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
def generate_section_summaries(title: str, full_text: str) -> SectionSummaries:
    llm = _llm()
    parser = PydanticOutputParser(pydantic_object=SectionSummaries)

    # Build prompt with parser's format instructions (enforces JSON shape)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a precise assistant for scientific summarization. "
                "Return ONLY valid JSON that conforms exactly to the schema and format instructions.",
            ),
            (
                "user",
                (
                    "Summarize the following scientific paper into four parts:\n\n"
                    f"Title: {title}\n\n"
                    "Requirements:\n"
                    "1) overall: 3-5 sentences\n"
                    "2) key_findings: list of short bullet strings (no numbering)\n"
                    "3) methods: 2-4 sentences\n"
                    "4) conclusions: 2-3 sentences\n"
                    "Keep it factual and faithful; do not invent details.\n\n"
                    "Paper Content (truncated if long):\n"
                    "{content}\n\n"
                    "FORMAT INSTRUCTIONS:\n{format_instructions}"
                ),
            ),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    # Run the chain: prompt -> LLM -> parse
    content = full_text[:120000] if full_text else ""
    msg = llm.invoke(prompt.format_messages(content=content))
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