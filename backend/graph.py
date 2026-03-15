"""
LangGraph pipeline definition.

Seven nodes wired in a linear chain — each one does one thing well,
then hands off to the next:

  query_rewriter → search_planner → web_search → document_filter
  → source_summaries → answer_generator → add_citations
"""

from langgraph.graph import StateGraph, END

from state import ResearchState
from nodes import (
    query_rewriter,
    search_planner,
    web_search,
    document_filter,
    source_summaries,
    answer_generator,
    add_citations,
)


def build_research_graph():
    """Wire up the nodes and compile the graph. Returns a runnable pipeline."""
    graph = StateGraph(ResearchState)

    # Register each node
    graph.add_node("query_rewriter", query_rewriter)
    graph.add_node("search_planner", search_planner)
    graph.add_node("web_search", web_search)
    graph.add_node("document_filter", document_filter)
    graph.add_node("source_summaries", source_summaries)
    graph.add_node("answer_generator", answer_generator)
    graph.add_node("add_citations", add_citations)

    # Simple linear flow — no branching needed here
    graph.set_entry_point("query_rewriter")
    graph.add_edge("query_rewriter", "search_planner")
    graph.add_edge("search_planner", "web_search")
    graph.add_edge("web_search", "document_filter")
    graph.add_edge("document_filter", "source_summaries")
    graph.add_edge("source_summaries", "answer_generator")
    graph.add_edge("answer_generator", "add_citations")
    graph.add_edge("add_citations", END)

    return graph.compile()


# Build once at import time so we don't recompile on every request
research_graph = build_research_graph()
