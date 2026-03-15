"""
Node implementations for the research pipeline.

Each function takes the shared ResearchState, does its thing, and returns
a partial state update. We use two LLM tiers through Groq:

  Fast  — Llama 4 Scout 17B  (query rewriting, filtering, summarization)
  Heavy — GPT-OSS 120B       (answer generation, citation injection)

Web search hits the Serper API (Google results).
"""

import os
import json
import re
import asyncio
import requests
from typing import List, Dict, Any

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from duckduckgo_search import DDGS
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from state import ResearchState


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _get_fast_llm() -> ChatGroq:
    """Llama 4 Scout — cheap and quick, great for structured extraction."""
    return ChatGroq(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0.3,
        groq_api_key=os.getenv("GROQ_API_KEY"),
    )


def _get_powerful_llm() -> ChatGroq:
    """GPT-OSS 120B — heavier model for tasks that need real reasoning."""
    return ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0.4,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        max_retries=3,
    )


def create_retry_decorator():
    """Exponential backoff for flaky LLM calls — waits 4s, 8s, 16s, 20s max."""
    return retry(
        wait=wait_exponential(multiplier=2, min=4, max=20),
        stop=stop_after_attempt(5),
    )


def _parse_json_response(content: str) -> dict:
    """
    Best-effort JSON parser for LLM output.

    Handles the usual issues: markdown fences, extra whitespace,
    JSON buried in surrounding text, etc.
    """
    cleaned = content.strip()

    # Strip ```json ... ``` fences
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Last resort: fish out the first JSON object from the text
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None


# ---------------------------------------------------------------------------
# Node 1 — Query Rewriter
# ---------------------------------------------------------------------------

async def query_rewriter(state: ResearchState) -> Dict[str, Any]:
    """
    Takes the raw user question, cleans it up for search engines,
    and generates sub-queries to cover different angles.
    """
    print(f"[query_rewriter] Processing: {state['original_query']}")
    llm = _get_fast_llm()

    prompt = f"""You are a search query optimization expert. Given a user's question, do two things:
1. Rewrite the question into a clear, concise, search-engine-friendly query.
2. Generate 2-4 sub-queries that explore different aspects of the question.

User Question: {state["original_query"]}

Respond in valid JSON only (no markdown, no explanation):
{{
  "rewritten_query": "...",
  "sub_queries": ["...", "...", "..."]
}}"""

    @create_retry_decorator()
    async def invoke_llm():
        return await llm.ainvoke([
            SystemMessage(content="You are a helpful search query optimizer. Always respond in valid JSON only, no markdown fences."),
            HumanMessage(content=prompt),
        ])

    response = await invoke_llm()

    result = _parse_json_response(response.content)
    if not result:
        # Fallback: just use the original query as-is
        result = {
            "rewritten_query": state["original_query"],
            "sub_queries": [state["original_query"]],
        }

    print(f"[query_rewriter] Rewritten: {result.get('rewritten_query')}")
    print(f"[query_rewriter] Sub-queries: {result.get('sub_queries')}")

    return {
        "rewritten_query": result["rewritten_query"],
        "sub_queries": result.get("sub_queries", [state["original_query"]]),
        "current_step": "query_rewriter",
        "steps_completed": state.get("steps_completed", []) + ["query_rewriter"],
    }


# ---------------------------------------------------------------------------
# Node 2 — Search Planner
# ---------------------------------------------------------------------------

async def search_planner(state: ResearchState) -> Dict[str, Any]:
    """
    Turns the rewritten query + sub-queries into a focused set
    of 3-5 search queries that should give us good coverage.
    """
    print(f"[search_planner] Planning searches...")
    llm = _get_fast_llm()

    sub_queries_text = "\n".join(f"- {q}" for q in state.get("sub_queries", []))

    prompt = f"""You are a research planner. Given the rewritten query and sub-queries below,
produce a list of 3-5 specific search queries that will find the most relevant and diverse information.

Rewritten Query: {state.get("rewritten_query", state["original_query"])}
Sub-queries:
{sub_queries_text}

Respond in valid JSON only (no markdown, no explanation):
{{
  "search_queries": ["query1", "query2", "query3"]
}}"""

    @create_retry_decorator()
    async def invoke_llm():
        return await llm.ainvoke([
            SystemMessage(content="You are a research planning assistant. Always respond in valid JSON only, no markdown fences."),
            HumanMessage(content=prompt),
        ])

    response = await invoke_llm()

    result = _parse_json_response(response.content)
    if not result:
        # If parsing fails, fall back to what we already have
        result = {
            "search_queries": [
                state.get("rewritten_query", state["original_query"])
            ] + state.get("sub_queries", [])
        }

    search_queries = result.get("search_queries", [state["original_query"]])
    print(f"[search_planner] Planned {len(search_queries)} queries: {search_queries}")

    return {
        "search_queries": search_queries,
        "current_step": "search_planner",
        "steps_completed": state.get("steps_completed", []) + ["search_planner"],
    }


# ---------------------------------------------------------------------------
# Node 3 — Web Search (Serper API)
# ---------------------------------------------------------------------------

async def web_search(state: ResearchState) -> Dict[str, Any]:
    """
    Fires off the planned queries against Google via the Serper API
    and collects the results, deduplicating by URL.
    """
    print(f"[web_search] Starting web searches...")

    raw_documents = []
    seen_urls = set()

    search_queries = state.get("search_queries", [state["original_query"]])

    for query in search_queries[:5]:  # don't go overboard
        try:
            print(f"[web_search] Searching: '{query}'")
            results = await asyncio.to_thread(_serper_search, query)

            for result in results:
                url = result.get("href", result.get("link", ""))
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    raw_documents.append({
                        "title": result.get("title", "Untitled"),
                        "url": url,
                        "snippet": result.get("body", result.get("snippet", "")),
                        "content": result.get("body", result.get("snippet", "")),
                    })
                    print(f"[web_search]   → Found: {result.get('title', 'Untitled')[:60]}")

        except Exception as e:
            print(f"[web_search] Error searching '{query}': {e}")
            continue

    print(f"[web_search] Total documents found: {len(raw_documents)}")

    return {
        "raw_documents": raw_documents,
        "current_step": "web_search",
        "steps_completed": state.get("steps_completed", []) + ["web_search"],
    }


@create_retry_decorator()
def _serper_search(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Hit the Serper API for Google search results."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        print("[_serper_search] Missing SERPER_API_KEY")
        return []

    url = "https://google.serper.dev/search"
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json',
    }
    # Request a couple extra to make sure we have enough after dedup
    payload = json.dumps({"q": query, "num": max_results + 2})

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("organic", []):
            results.append({
                "title": item.get("title", ""),
                "href": item.get("link", ""),
                "body": item.get("snippet", ""),
            })
            if len(results) >= max_results:
                break

        return results
    except Exception as e:
        print(f"[_serper_search] Serper API error for '{query}': {e}")
        return []


# ---------------------------------------------------------------------------
# Node 4 — Document Filter
# ---------------------------------------------------------------------------

async def document_filter(state: ResearchState) -> Dict[str, Any]:
    """
    Uses LLM to score and filter documents for relevance.
    Keeps only the ones that actually help answer the question.
    """
    raw_docs = state.get("raw_documents", [])
    print(f"[document_filter] Filtering {len(raw_docs)} documents...")

    if not raw_docs:
        print("[document_filter] No documents to filter!")
        return {
            "filtered_documents": [],
            "current_step": "document_filter",
            "steps_completed": state.get("steps_completed", []) + ["document_filter"],
        }

    llm = _get_fast_llm()

    docs_text = ""
    for i, doc in enumerate(raw_docs[:15]):
        docs_text += f"\n[{i}] Title: {doc['title']}\n    URL: {doc['url']}\n    Snippet: {doc['snippet'][:300]}\n"

    prompt = f"""You are a document relevance filter. Given the user's original question and a list of
search results, identify which documents are relevant and would help answer the question.

Original Question: {state["original_query"]}

Documents:
{docs_text}

Return a JSON list of the indices (numbers) of relevant documents, ordered by relevance.
Respond in valid JSON only (no markdown):
{{
  "relevant_indices": [0, 2, 5]
}}"""

    @create_retry_decorator()
    async def invoke_llm():
        return await llm.ainvoke([
            SystemMessage(content="You are a relevance filter. Always respond in valid JSON only, no markdown fences."),
            HumanMessage(content=prompt),
        ])

    response = await invoke_llm()

    result = _parse_json_response(response.content)
    if result:
        indices = result.get("relevant_indices", list(range(len(raw_docs))))
    else:
        indices = list(range(min(len(raw_docs), 8)))

    filtered = [raw_docs[i] for i in indices if i < len(raw_docs)]

    # Safety net: don't return nothing
    if not filtered:
        filtered = raw_docs[:5]

    print(f"[document_filter] Kept {len(filtered)} relevant documents")

    return {
        "filtered_documents": filtered,
        "current_step": "document_filter",
        "steps_completed": state.get("steps_completed", []) + ["document_filter"],
    }


# ---------------------------------------------------------------------------
# Node 5 — Source Summaries
# ---------------------------------------------------------------------------

async def source_summaries(state: ResearchState) -> Dict[str, Any]:
    """
    Generates a 1-2 sentence summary of each filtered document,
    focused on what's relevant to the user's question.
    """
    filtered_docs = state.get("filtered_documents", [])
    print(f"[source_summaries] Summarizing {len(filtered_docs)} documents...")

    if not filtered_docs:
        return {
            "summaries": [],
            "current_step": "source_summaries",
            "steps_completed": state.get("steps_completed", []) + ["source_summaries"],
        }

    llm = _get_fast_llm()

    docs_text = ""
    for i, doc in enumerate(filtered_docs[:10]):
        docs_text += f"\n[{i}] Title: {doc['title']}\n    URL: {doc['url']}\n    Content: {doc.get('content', doc['snippet'])[:400]}\n"

    prompt = f"""You are a research summarizer. For each document below, write a 1-2 sentence summary
capturing the key information relevant to the question: "{state['original_query']}"

Documents:
{docs_text}

Respond in valid JSON only (no markdown):
{{
  "summaries": [
    {{"index": 0, "summary": "..."}},
    {{"index": 1, "summary": "..."}}
  ]
}}"""

    @create_retry_decorator()
    async def invoke_llm():
        return await llm.ainvoke([
            SystemMessage(content="You are a research summarizer. Always respond in valid JSON only, no markdown fences."),
            HumanMessage(content=prompt),
        ])

    response = await invoke_llm()

    summaries = []
    result = _parse_json_response(response.content)
    if result:
        for item in result.get("summaries", []):
            idx = item.get("index", 0)
            if idx < len(filtered_docs):
                summaries.append({
                    "title": filtered_docs[idx]["title"],
                    "url": filtered_docs[idx]["url"],
                    "summary": item.get("summary", ""),
                })

    # If the LLM didn't cooperate, just use the raw snippets
    if not summaries:
        for doc in filtered_docs:
            summaries.append({
                "title": doc["title"],
                "url": doc["url"],
                "summary": doc["snippet"][:200],
            })

    print(f"[source_summaries] Generated {len(summaries)} summaries")

    return {
        "summaries": summaries,
        "current_step": "source_summaries",
        "steps_completed": state.get("steps_completed", []) + ["source_summaries"],
    }


# ---------------------------------------------------------------------------
# Node 6 — Answer Generator
# ---------------------------------------------------------------------------

async def answer_generator(state: ResearchState) -> Dict[str, Any]:
    """
    Synthesizes all the source summaries into a comprehensive, markdown-
    formatted answer. This is where the heavy LLM earns its keep.
    """
    print(f"[answer_generator] Generating answer...")
    llm = _get_powerful_llm()

    summaries = state.get("summaries", [])
    sources_text = ""
    for i, s in enumerate(summaries):
        sources_text += f"\n[Source {i+1}] {s['title']}\n  URL: {s['url']}\n  Summary: {s['summary']}\n"

    prompt = f"""You are an expert research assistant. Based on the source summaries below,
generate a comprehensive, well-structured answer to the user's question.

Requirements:
- Write in clear, informative paragraphs
- Use markdown formatting (headers, bold, bullet points) for readability
- Be thorough but concise
- Reference information from sources naturally (e.g., "According to research...", "Studies show...")
- Do NOT include citation numbers yet (that will be added in the next step)
- If sources conflict, acknowledge different perspectives

User's Original Question: {state["original_query"]}
Rewritten Query: {state.get("rewritten_query", state["original_query"])}

Source Summaries:
{sources_text if sources_text else "No sources available. Provide a general answer based on your knowledge."}

Write a comprehensive answer:"""

    @create_retry_decorator()
    async def invoke_llm():
        return await llm.ainvoke([
            SystemMessage(content="You are an expert research assistant who synthesizes information from multiple sources into clear, comprehensive answers."),
            HumanMessage(content=prompt),
        ])

    response = await invoke_llm()

    print(f"[answer_generator] Answer generated ({len(response.content)} chars)")

    return {
        "answer": response.content,
        "current_step": "answer_generator",
        "steps_completed": state.get("steps_completed", []) + ["answer_generator"],
    }


# ---------------------------------------------------------------------------
# Node 7 — Add Citations
# ---------------------------------------------------------------------------

async def add_citations(state: ResearchState) -> Dict[str, Any]:
    """
    Injects inline citation markers ([1], [2], etc.) into the answer text
    and builds the final citations list for the frontend.
    """
    print(f"[add_citations] Adding citations...")
    llm = _get_powerful_llm()

    answer = state.get("answer", "")
    summaries = state.get("summaries", [])

    if not summaries:
        return {
            "cited_answer": answer,
            "citations": [],
            "current_step": "add_citations",
            "steps_completed": state.get("steps_completed", []) + ["add_citations"],
        }

    sources_text = ""
    for i, s in enumerate(summaries):
        sources_text += f"[{i+1}] {s['title']} - {s['url']}\n    {s['summary']}\n"

    prompt = f"""You are a citation specialist. Given the answer and source list below,
add inline citation numbers like [1], [2], etc. where information from a specific source is used.

Rules:
- Add citation numbers at the end of sentences or claims that use information from a source
- Only cite sources whose information is actually reflected in the answer
- Keep the answer text intact, only adding citation numbers
- Use the format [1], [2], etc. matching the source numbers below

Answer:
{answer}

Sources:
{sources_text}

Return the answer with citations added. Only return the modified answer text, nothing else."""

    @create_retry_decorator()
    async def invoke_llm():
        return await llm.ainvoke([
            SystemMessage(content="You are a citation specialist. Add inline citations to the text. Return ONLY the modified answer text."),
            HumanMessage(content=prompt),
        ])

    response = await invoke_llm()

    citations = [{"title": s["title"], "url": s["url"], "summary": s["summary"]} for s in summaries]

    print(f"[add_citations] Done — {len(citations)} citations attached")

    return {
        "cited_answer": response.content,
        "citations": citations,
        "current_step": "add_citations",
        "steps_completed": state.get("steps_completed", []) + ["add_citations"],
    }
