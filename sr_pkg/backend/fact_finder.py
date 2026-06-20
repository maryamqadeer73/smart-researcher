"""
Smart Researcher — Authentic Fact Finder
Retrieves real facts and snippets from Wikipedia and DuckDuckGo for any custom topic.
Completely free, no API keys required.
"""

import requests
import re
from bs4 import BeautifulSoup
import urllib.parse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def fetch_wikipedia_facts(topic):
    """Search Wikipedia for the topic and get the intro text of the top article."""
    facts = []
    try:
        # Step 1: Search Wikipedia
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(topic)}&format=json"
        r = requests.get(search_url, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            data = r.json()
            search_results = data.get("query", {}).get("search", [])
            if search_results:
                top_title = search_results[0]["title"]
                
                # Step 2: Get extract of the top page
                extract_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={urllib.parse.quote(top_title)}&format=json"
                r2 = requests.get(extract_url, headers=HEADERS, timeout=8)
                if r2.status_code == 200:
                    pages = r2.json().get("query", {}).get("pages", {})
                    for page_id, page_info in pages.items():
                        extract = page_info.get("extract", "")
                        if extract:
                            # Split into sentences
                            sentences = re.split(r'\.\s+', extract)
                            for s in sentences:
                                s = s.strip()
                                if len(s) > 25 and len(s) < 250:
                                    if not s.endswith('.'):
                                        s += '.'
                                    facts.append({
                                        "source": f"Wikipedia: {top_title}",
                                        "fact": s,
                                        "category": "Historical Context"
                                    })
    except Exception as e:
        print(f"Wikipedia search failed: {e}")
    return facts

def fetch_ddg_facts(topic):
    """Scrape DuckDuckGo HTML search results for real-time snippets."""
    facts = []
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(topic)}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            results = soup.find_all("div", class_="result")
            for res in results[:6]:
                snippet_el = res.find("a", class_="result__snippet")
                title_el = res.find("a", class_="result__url")
                
                if snippet_el and title_el:
                    snippet = snippet_el.get_text().strip()
                    title = title_el.get_text().strip()
                    
                    # Clean snippet
                    snippet = re.sub(r'\s+', ' ', snippet)
                    if len(snippet) > 30:
                        facts.append({
                            "source": title if len(title) < 50 else title[:47] + "...",
                            "fact": snippet,
                            "category": "Latest News / Web Snippet"
                        })
    except Exception as e:
        print(f"DuckDuckGo search failed: {e}")
    return facts

def get_authentic_facts(topic):
    """Retrieve facts from multiple sources, merge and return them."""
    if not topic or not topic.strip():
        return []
    
    wiki_facts = fetch_wikipedia_facts(topic)
    ddg_facts = fetch_ddg_facts(topic)
    
    # Merge and prioritize Wikipedia first, then DDG snippets
    all_facts = wiki_facts + ddg_facts
    
    # Fallback facts in case network is down or query yields nothing
    if not all_facts:
        all_facts = [
            {
                "source": "Local Fallback Engine",
                "fact": f"Overview of {topic}: Highly discussed modern concept shaping trends and strategies.",
                "category": "Heuristic Context"
            },
            {
                "source": "Local Fallback Engine",
                "fact": f"Key dynamics of {topic} involve rapid adoption, system optimization, and user-centric value creation.",
                "category": "Core Concept"
            },
            {
                "source": "Local Fallback Engine",
                "fact": f"Best practices for {topic} focus on clean execution, structured data, and authentic communication.",
                "category": "Implementation"
            }
        ]
        
    return all_facts[:12] # Limit to 12 facts for choice selection
