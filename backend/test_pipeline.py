import asyncio
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from graph import research_graph

async def test_search(query: str):
    print(f"\n========================================================")
    print(f"Testing Backend Research Pipeline for: '{query}'")
    print(f"========================================================\n")
    
    initial_state = {
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

    try:
        # Stream the progress so we can see where rate limits hit or succeed
        async for event in research_graph.astream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                print(f"--------------------------------------------------")
                print(f"✅ Node Completed: {node_name}")
                
                # Print interesting output
                if node_name == "query_rewriter":
                    print(f"   Rewritten: {node_output.get('rewritten_query')}")
                elif node_name == "search_planner":
                    print(f"   Searches: {node_output.get('search_queries')}")
                elif node_name == "web_search":
                    print(f"   Docs Found: {len(node_output.get('raw_documents', []))}")
                elif node_name == "document_filter":
                    print(f"   Docs Filtered: {len(node_output.get('filtered_documents', []))}")
                elif node_name == "source_summaries":
                    print(f"   Summaries Done: {len(node_output.get('summaries', []))}")
                elif node_name == "answer_generator":
                    ans = node_output.get("answer", "")
                    print(f"   Answer length: {len(ans)} chars")
                elif node_name == "add_citations":
                    c_ans = node_output.get("cited_answer", "")
                    print(f"   Cited Answer length: {len(c_ans)} chars")
                    print(f"   Citations: {len(node_output.get('citations', []))}")

        print(f"\n========================================================")
        print(f"🎉 Pipeline Completed Successfully!")
        print(f"========================================================\n")
        
    except Exception as e:
        print(f"\n❌ Pipeline Failed with Error: {e}")

if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY is missing in your .env file.")
        exit(1)
        
    # The user's requested query
    test_query = "current lpg crisis of the india"
    asyncio.run(test_search(test_query))
