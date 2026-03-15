"""
FastAPI server for the AI Research Search Engine.

Exposes three endpoints:
  POST /api/search        — run the full pipeline, return the result
  POST /api/search/stream — stream each step's progress via SSE
  GET  /api/health        — quick health check
"""

import os
import json
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Need env vars loaded before importing the graph (it reads GROQ_API_KEY on init)
load_dotenv()

from graph import research_graph
from state import ResearchState


# ---------------------------------------------------------------------------
# Lifespan — just checks that API keys are configured
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Log which API keys are set so we catch config issues early."""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        print("⚠️  WARNING: GROQ_API_KEY environment variable is not set!")
        print("   Set it in backend/.env or export it before running.")
    else:
        print("✅ GROQ_API_KEY detected")

    serper_key = os.getenv("SERPER_API_KEY")
    if not serper_key:
        print("⚠️  WARNING: SERPER_API_KEY environment variable is not set!")
        print("   Set it in backend/.env or export it before running.")
    else:
        print("✅ SERPER_API_KEY detected")

    print("🚀 AI Research Search Engine backend is ready!")
    yield
    print("👋 Shutting down…")


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Research Search Engine",
    description="LangGraph-powered research pipeline that searches, filters, summarizes, and answers questions with citations.",
    version="1.0.0",
    lifespan=lifespan,
)

# Let the React dev server talk to us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str


class SearchResponse(BaseModel):
    original_query: str
    rewritten_query: str
    answer: str
    cited_answer: str
    citations: list
    sources_count: int
    steps_completed: list


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_initial_state(query: str) -> ResearchState:
    """Build a blank pipeline state from a raw user query."""
    return {
        "original_query": query,
        "rewritten_query": "",
        "sub_queries": [],
        "search_queries": [],
        "raw_documents": [],
        "filtered_documents": [],
        "summaries": [],
        "answer": "",
        "cited_answer": "",
        "citations": [],
        "current_step": "",
        "steps_completed": [],
        "error": None,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "groq_key_set": bool(os.getenv("GROQ_API_KEY")),
        "serper_key_set": bool(os.getenv("SERPER_API_KEY")),
    }


@app.post("/api/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    """Run the full research pipeline and return the final result."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        result = await research_graph.ainvoke(_make_initial_state(req.query.strip()))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    return SearchResponse(
        original_query=result.get("original_query", req.query),
        rewritten_query=result.get("rewritten_query", ""),
        answer=result.get("answer", ""),
        cited_answer=result.get("cited_answer", result.get("answer", "")),
        citations=result.get("citations", []),
        sources_count=len(result.get("citations", [])),
        steps_completed=result.get("steps_completed", []),
    )


@app.post("/api/search/stream")
async def search_stream(req: SearchRequest):
    """
    Stream pipeline progress via Server-Sent Events.

    Each node fires an SSE event when it completes, so the frontend
    can update the progress indicator in real time.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    initial_state = _make_initial_state(req.query.strip())

    async def event_generator():
        try:
            async for event in research_graph.astream(initial_state, stream_mode="updates"):
                for node_name, node_output in event.items():
                    step_data = {
                        "step": node_name,
                        "steps_completed": node_output.get("steps_completed", []),
                    }

                    # Attach the interesting bits from each step
                    if node_name == "query_rewriter":
                        step_data["rewritten_query"] = node_output.get("rewritten_query", "")
                        step_data["sub_queries"] = node_output.get("sub_queries", [])
                    elif node_name == "search_planner":
                        step_data["search_queries"] = node_output.get("search_queries", [])
                    elif node_name == "web_search":
                        step_data["documents_found"] = len(node_output.get("raw_documents", []))
                    elif node_name == "document_filter":
                        step_data["filtered_count"] = len(node_output.get("filtered_documents", []))
                    elif node_name == "source_summaries":
                        step_data["summaries_count"] = len(node_output.get("summaries", []))
                        step_data["summaries"] = node_output.get("summaries", [])
                    elif node_name == "answer_generator":
                        step_data["answer"] = node_output.get("answer", "")
                    elif node_name == "add_citations":
                        step_data["cited_answer"] = node_output.get("cited_answer", "")
                        step_data["citations"] = node_output.get("citations", [])

                    yield f"data: {json.dumps(step_data)}\n\n"

            yield f"data: {json.dumps({'step': 'complete'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # important for nginx proxies
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
