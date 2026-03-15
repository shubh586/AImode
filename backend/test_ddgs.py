import time
from duckduckgo_search import DDGS

def test_search():
    queries = [
        "US Iran relations 2026",
        "US Iran current news",
        "US Iran conflict latest",
        "Iran nuclear deal status"
    ]
    with DDGS() as ddgs:
        for q in queries:
            try:
                print(f"Searching: {q}")
                results = list(ddgs.text(q, max_results=3))
                print(f"Found {len(results)} results")
                time.sleep(2)
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    test_search()
