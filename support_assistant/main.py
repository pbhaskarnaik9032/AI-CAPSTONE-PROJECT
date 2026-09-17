import os
import json
from pathlib import Path
from typing import TypedDict, Literal

import chromadb
from fastapi import FastAPI
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from langgraph.graph import StateGraph, START, END

# SETTINGS
BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
CHROMA_DIR = BASE_DIR / "chroma_db"

MOCK_LLM = os.getenv("MOCK_LLM", "1") != "0"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "zepto_policies"
CHUNK_SIZE = 400
CHUNK_OVERLAP = 80

# LOAD EMBEDDING MODEL
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

# CHROMADB
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)

# DOCUMENT CHUNKING
def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split a document into overlapping character chunks."""
    text = " ".join(text.split())

    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks

# LOAD DOCUMENTS AND CREATE CHUNKS
def load_documents():
    documents = []
    ids = []
    metadatas = []

    for file in sorted(DOCS_DIR.glob("doc_*.txt")):
        text = file.read_text(encoding="utf-8").strip()
        chunks = chunk_text(text)

        for chunk_number, chunk in enumerate(chunks, start=1):
            documents.append(chunk)
            ids.append(f"{file.stem}_chunk_{chunk_number}")
            metadatas.append({
                "source": file.name,
                "document_id": file.stem,
                "chunk_id": chunk_number
            })

    return documents, ids, metadatas


def build_vector_store():
    documents, ids, metadatas = load_documents()

    # Remove legacy document-level IDs from the earlier implementation.
    legacy_ids = [f"doc_{number:02d}" for number in range(1, 9)]
    collection.delete(ids=legacy_ids)

    embeddings = embedding_model.encode(
        documents,
        normalize_embeddings=True
    ).tolist()

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return len(documents)


chunk_count = build_vector_store()

# STRUCTURED OUTPUT
class AnswerResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence: float = Field(ge=0, le=1)


class AskRequest(BaseModel):
    query: str


# LANGGRAPH STATE
class SupportState(TypedDict):
    query: str
    intent: str
    retrieved_chunks: list[dict]
    answer: str
    sources: list[str]
    confidence: float


# STRUCTURED PROMPT
STRUCTURED_PROMPT = """
ROLE:
You are a Zepto customer support assistant.

CONTEXT:
Use only the policy information provided below.

TASK:
Answer the user's question using the provided policy context.

FORMAT:
Return valid JSON with exactly these fields:
{
  "answer": "string",
  "sources": ["document_id"],
  "confidence": 0.0
}

LENGTH:
Keep the answer short and clear.

NEGATIVE CONSTRAINT:
Do not answer using information that is not present in the provided context.
Do not invent Zepto policies.

FEW-SHOT EXAMPLE:

Question:
How long does delivery usually take?

Context:
Zepto delivers grocery and household essentials within 10 to 30 minutes of order confirmation.

Answer:
{
  "answer": "Zepto deliveries take 10 to 30 minutes of order confirmation.",
  "sources": ["doc_01"],
  "confidence": 1.0
}

Now answer the new question using only the supplied context.
"""

# INTENT CLASSIFICATION
def classify_intent(state: SupportState):
    query = state["query"].lower()
    policy_keywords = [
        "delivery",
        "return",
        "refund",
        "membership",
        "tracking",
        "cancel",
        "gift card",
        "support hours"
    ]

    if MOCK_LLM:
        if any(keyword in query for keyword in policy_keywords):
            intent = "policy_question"
        else:
            intent = "general_question"
    else:
        intent = real_llm_classify(query)

    return {"intent": intent}


# RETRIEVAL
def retrieve_chunks(query):
    query_embedding = embedding_model.encode(
        [query],
        normalize_embeddings=True
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        })

    return chunks


# RETRIEVE + ANSWER
def retrieve_and_answer(state: SupportState):
    query = state["query"]
    chunks = retrieve_chunks(query)

    # Return source document IDs rather than internal chunk IDs.
    sources = []
    for chunk in chunks:
        document_id = chunk["metadata"].get("document_id", chunk["id"])
        if document_id not in sources:
            sources.append(document_id)

    if MOCK_LLM:
        top_chunk = chunks[0]["document"]
        answer = "Based on the retrieved context: " + top_chunk[:200]
        confidence = 1.0
    else:
        answer_data = real_llm_answer(query, chunks)
        answer = answer_data.answer
        sources = answer_data.sources
        confidence = answer_data.confidence

    return {
        "retrieved_chunks": chunks,
        "answer": answer,
        "sources": sources,
        "confidence": confidence
    }


# GENERAL ANSWER
def direct_answer(state: SupportState):
    if MOCK_LLM:
        answer = "I can only answer questions about Zepto policies right now."
        return {
            "answer": answer,
            "sources": [],
            "confidence": 1.0
        }

    answer_data = real_llm_general_answer(state["query"])
    return {
        "answer": answer_data.answer,
        "sources": [],
        "confidence": answer_data.confidence
    }


# ROUTER
def route_intent(
    state: SupportState
) -> Literal["retrieve_and_answer", "direct_answer"]:
    if state["intent"] == "policy_question":
        return "retrieve_and_answer"
    return "direct_answer"


# OPTIONAL REAL LLM CLASSIFICATION
def real_llm_classify(query):
    prompt = f"""
Classify this query as exactly one of:
policy_question
general_question
Query:
{query}
Return only the classification.
"""

    result = call_real_llm(prompt)
    result = result.strip().lower()

    if "policy_question" in result:
        return "policy_question"

    return "general_question"


# OPTIONAL REAL LLM ANSWER
def real_llm_answer(query, chunks):
    context = "\n\n".join(
        [
            f"{chunk['id']}: {chunk['document']}"
            for chunk in chunks
        ]
    )

    prompt = (
        STRUCTURED_PROMPT
        + "\n\nUSER QUESTION:\n"
        + query
        + "\n\nRETRIEVED CONTEXT:\n"
        + context
    )

    return call_and_validate(
        prompt,
        sources=[
            chunk["metadata"].get("document_id", chunk["id"])
            for chunk in chunks
        ]
    )


# OPTIONAL GENERAL LLM ANSWER
def real_llm_general_answer(query):
    prompt = """
ROLE:
You are a Zepto customer support assistant.

CONTEXT:
There is no policy retrieval context for this query.

TASK:
Answer the user's question directly.

FORMAT:
Return valid JSON with:
answer
sources
confidence

LENGTH:
Keep the answer short.

NEGATIVE CONSTRAINT:
Do not invent Zepto policy information.

Question:
""" + query

    return call_and_validate(prompt, sources=[])


# VALIDATION + RETRIES
def call_and_validate(prompt, sources):
    last_error = ""

    for attempt in range(3):
        try:
            response_text = call_real_llm(prompt)
            data = json.loads(response_text)
            result = AnswerResponse.model_validate(data)
            return result
        except Exception as error:
            last_error = str(error)
            prompt = (
                prompt
                + "\n\nCORRECTIVE INSTRUCTION:\n"
                "Return ONLY valid JSON containing "
                "answer, sources, and confidence. "
                "No markdown. No extra text."
            )

    return AnswerResponse(
        answer=f"ERROR: Could not validate LLM response. {last_error}",
        sources=sources,
        confidence=0.0
    )


# OPTIONAL REAL LLM HTTP CALL
def call_real_llm(prompt):
    import requests

    api_url = os.getenv("LLM_API_URL")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")

    if not api_url or not api_key or not model:
        raise RuntimeError(
            "Set LLM_API_URL, LLM_API_KEY and LLM_MODEL "
            "when MOCK_LLM=0."
        )

    response = requests.post(
        api_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0
        },
        timeout=60
    )

    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


# LANGGRAPH
graph_builder = StateGraph(SupportState)
graph_builder.add_node("classify_intent", classify_intent)
graph_builder.add_node("retrieve_and_answer", retrieve_and_answer)
graph_builder.add_node("direct_answer", direct_answer)
graph_builder.add_edge(START, "classify_intent")
graph_builder.add_conditional_edges("classify_intent", route_intent)
graph_builder.add_edge("retrieve_and_answer", END)
graph_builder.add_edge("direct_answer", END)
graph = graph_builder.compile()


# HELPER FUNCTION
def ask_question(query):
    result = graph.invoke(
        {
            "query": query,
            "intent": "",
            "retrieved_chunks": [],
            "answer": "",
            "sources": [],
            "confidence": 0.0
        }
    )

    return AnswerResponse(
        answer=result["answer"],
        sources=result["sources"],
        confidence=result["confidence"]
    )


# FASTAPI
app = FastAPI(title="Zepto GenAI Support Assistant")


@app.get("/")
def home():
    return {
        "message": "Zepto Support Assistant is running",
        "documents_loaded": 8,
        "chunks_indexed": chunk_count,
        "mock_llm": MOCK_LLM
    }


@app.post("/ask", response_model=AnswerResponse)
def ask(request: AskRequest):
    return ask_question(request.query)
