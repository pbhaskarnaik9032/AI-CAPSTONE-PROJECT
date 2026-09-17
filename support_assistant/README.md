# Module 3 - GenAI Support Assistant

A grounded Zepto policy support assistant using RAG, ChromaDB, LangGraph, Pydantic, Sentence Transformers, and FastAPI.

## Architecture

The application follows this pipeline:

```text
User Question
     ↓
Document Loading
     ↓
Text Chunking
     ↓
all-MiniLM-L6-v2 Embeddings
     ↓
Persistent ChromaDB
     ↓
LangGraph classify_intent
     ↓
 ┌───────────────────────┐
 │                       │
policy_question      general_question
 │                       │
 ↓                       ↓
retrieve_and_answer   direct_answer
 │                       │
 ↓                       ↓
Top-3 relevant chunks   Fixed mock response
 │
 ↓
Structured Pydantic Response
 │
 ↓
FastAPI POST /ask
```

## Ingestion

The eight Zepto policy documents are stored in the `docs/` folder.

`main.py` loads all `doc_*.txt` files, normalizes their text, and splits each document into overlapping chunks before creating embeddings.

The current chunking configuration is:

- Chunk size: 400 characters
- Chunk overlap: 80 characters

Each chunk receives a unique ChromaDB ID such as `doc_01_chunk_1` and stores metadata containing the original document ID and chunk number.

## Embedding

The application uses the `all-MiniLM-L6-v2` Sentence Transformer model.

The chunk embeddings are stored in a persistent ChromaDB collection named:

`zepto_policies`

Cosine similarity is used for retrieval.

## Retrieval

The `retrieve_and_answer` LangGraph node embeds the user query and retrieves the top 3 most similar chunks from ChromaDB.

The original document IDs are returned in the `sources` field, while the internal chunk IDs remain in the vector store metadata.

## Generation

The LangGraph contains three required nodes:

- `classify_intent`
- `retrieve_and_answer`
- `direct_answer`

`classify_intent` uses the required keyword heuristic in mock mode.

Policy questions go to `retrieve_and_answer`.

General questions go to `direct_answer`.

## MOCK_LLM

The required graded mode uses `MOCK_LLM` unset or set to `1`.

In mock mode:

- no external LLM API is called
- intent classification uses the required keyword heuristic
- policy answers are generated from the top retrieved chunk
- general questions receive the fixed canned response
- the response is validated using the Pydantic schema

The optional `MOCK_LLM=0` path supports a real LLM and includes retry logic for invalid structured output.

## Structured Response

The API returns the following JSON structure:

```json
{
  "answer": "string",
  "sources": ["document_id"],
  "confidence": 1.0
}
```

## FastAPI

The application is wrapped in FastAPI and exposes a `POST /ask` endpoint.

The request format is:

```json
{
  "query": "How long does delivery take?"
}
```

The response contains:

- `answer`
- `sources`
- `confidence`

The root endpoint also reports the number of loaded source documents, indexed chunks, and whether mock mode is enabled.

## Example 1 - Policy Question

### Request

```bash
curl -X POST "http://127.0.0.1:7860/ask" \
-H "Content-Type: application/json" \
-d '{"query":"How long does delivery take?"}'
```

### Example Response

```json
{
  "answer": "Based on the retrieved context: Zepto delivers grocery and household essentials to serviceable pin codes within 10 to 30 minutes of order confirmation, depending on the customer's delivery zone and current order volume...",
  "sources": ["doc_01", "doc_02", "doc_04"],
  "confidence": 1.0
}
```

This query follows the policy retrieval path and uses the top retrieved chunk to generate the mock answer.

## Example 2 - General Question

### Request

```bash
curl -X POST "http://127.0.0.1:7860/ask" \
-H "Content-Type: application/json" \
-d '{"query":"What is the capital of India?"}'
```

### Response

```json
{
  "answer": "I can only answer questions about Zepto policies right now.",
  "sources": [],
  "confidence": 1.0
}
```

This query follows the direct-answer path because it is not classified as a Zepto policy question in mock mode.

## Docker

The application includes a `Dockerfile` for local execution.

### Build the Docker image

Run these commands from the `support_assistant/` directory:

```bash
docker build -t zepto-support .
```

### Run the container

```bash
docker run --rm -p 7860:7860 zepto-support
```

The FastAPI application will be available at:

`http://127.0.0.1:7860`

## Project Structure

```text
support_assistant/
├── docs/
│   ├── doc_01.txt
│   ├── doc_02.txt
│   ├── doc_03.txt
│   ├── doc_04.txt
│   ├── doc_05.txt
│   ├── doc_06.txt
│   ├── doc_07.txt
│   └── doc_08.txt
├── main.py
├── requirements.txt
├── Dockerfile
└── README.md
```
