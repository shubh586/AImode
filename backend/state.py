"""
Defines the state that gets passed between nodes in the LangGraph pipeline.

Each node reads from and writes to this shared TypedDict, progressively
building up the research result from raw query to cited answer.
"""

from typing import TypedDict, List, Optional


class SourceDocument(TypedDict):
    """A raw document pulled from the web — title, url, snippet, and full content."""
    title: str
    url: str
    snippet: str
    content: str


class SourceSummary(TypedDict):
    """A condensed version of a source, used for citations and display."""
    title: str
    url: str
    summary: str


class ResearchState(TypedDict):
    """
    Shared state for the research pipeline.

    Each node populates its own fields as the pipeline progresses:
      1. query_rewriter   → rewritten_query, sub_queries
      2. search_planner   → search_queries
      3. web_search       → raw_documents
      4. document_filter  → filtered_documents
      5. source_summaries → summaries
      6. answer_generator → answer
      7. add_citations    → cited_answer, citations
    """

    # The question the user actually typed
    original_query: str

    # Cleaned up version of the query, optimized for search
    rewritten_query: str
    sub_queries: List[str]

    # Final search queries we'll send to the web
    search_queries: List[str]

    # Everything we got back from search
    raw_documents: List[SourceDocument]

    # Subset that actually looks relevant
    filtered_documents: List[SourceDocument]

    # One-liner summaries of each relevant source
    summaries: List[SourceSummary]

    # LLM-generated answer (before and after citation injection)
    answer: str
    cited_answer: str
    citations: List[SourceSummary]

    # Tracks where we are in the pipeline
    current_step: str
    steps_completed: List[str]
    error: Optional[str]
