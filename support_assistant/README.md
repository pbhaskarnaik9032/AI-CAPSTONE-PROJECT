# Module 3 - GenAI Support Assistant

A grounded Zepto policy support assistant using RAG, ChromaDB, LangGraph, Pydantic, and FastAPI.

## Architecture

The application follows this pipeline:

```text
User Question
     ↓
Document / Query Processing
     ↓
all-MiniLM-L6-v2 Embeddings
     ↓
ChromaDB
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
