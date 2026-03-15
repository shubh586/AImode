import requests
from bs4 import BeautifulSoup
import time

def scrape_ddg(query: str, max_results=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = f"https://lite.duckduckgo.com/lite/"
    data = {"q": query}
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        for i, tr in enumerate(soup.find_all("tr")):
            td = tr.find("td", class_="result-snippet")
            if td:
                snippet = td.get_text(strip=True)
                
                # The title and link are usually in the preceding TR
                prev_tr = tr.find_previous_sibling("tr")
                if prev_tr:
                    a_tag = prev_tr.find("a", class_="result-url")
                    if not a_tag:
                        a_tag = prev_tr.find("a")
                        
                    if a_tag:
                        title = a_tag.get_text(strip=True)
                        link = a_tag.get("href")
                        results.append({
                            "title": title,
                            "href": link,
                            "body": snippet
                        })
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        print(f"Error scraping {query}: {e}")
        return []

if __name__ == "__main__":
    print(scrape_ddg("US Iran current news"))
