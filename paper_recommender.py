#!/usr/bin/env python3
"""
paper_recommender.py

Interfaces with Semantic Scholar Recommendations API to discover diverse,
non-repeating research paper recommendations based on seed papers and topics.
"""

import json
import pathlib
import requests
import random

CONFIG_PATH = pathlib.Path(__file__).parent / "config.json"
HISTORY_PATH = pathlib.Path(__file__).parent / "history.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_history():
    if HISTORY_PATH.exists():
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_history(history_set):
    # Keep last 200 items in history
    history_list = list(history_set)[-200:]
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history_list, f, indent=2)

def get_paper_recommendations(limit=25):
    config = load_config()
    seed_papers = config.get("seed_papers", [])
    history = load_history()
    
    # Extract IDs & randomly shuffle/sample seed subset to introduce diversity
    seed_ids = [p["id"] for p in seed_papers if "id" in p]
    if len(seed_ids) > 2:
        # Pick a random subset of 2-3 seed papers to vary recommendation embedding space
        sample_size = random.randint(2, min(4, len(seed_ids)))
        selected_seeds = random.sample(seed_ids, sample_size)
    else:
        selected_seeds = seed_ids
        
    print(f"🔍 Querying Semantic Scholar with {len(selected_seeds)} randomized seed papers...")
    
    url = "https://api.semanticscholar.org/recommendations/v1/papers/"
    payload = {
        "positivePaperIds": selected_seeds,
        "negativePaperIds": []
    }
    params = {
        "fields": "title,abstract,authors,year,externalIds,openAccessPdf,citationCount,venue,publicationDate",
        "limit": limit
    }
    
    headers = {"User-Agent": "NotebookLM-Podcast-Bot/1.0"}
    
    valid_papers = []
    try:
        res = requests.post(url, json=payload, params=params, headers=headers, timeout=15)
        res.raise_for_status()
        data = res.json()
        recommendations = data.get("recommendedPapers", [])
        print(f"✅ Semantic Scholar returned {len(recommendations)} candidate recommendations.")
        
        for p in recommendations:
            oa_pdf = p.get("openAccessPdf")
            external_ids = p.get("externalIds", {})
            
            pdf_url = None
            if oa_pdf and oa_pdf.get("url"):
                pdf_url = oa_pdf["url"]
            elif external_ids.get("ArXiv"):
                pdf_url = f"https://arxiv.org/pdf/{external_ids['ArXiv']}.pdf"

            if pdf_url:
                title = p.get("title", "Untitled Paper")
                s2_id = p.get("paperId", title)
                citations = p.get("citationCount", 0)
                min_citations = config.get("min_citations", 5)
                
                # Ensure paper is credible (>= min_citations OR published recently in 2025/2026) and unseen
                is_credible = (citations >= min_citations) or (p.get("year") and p.get("year") >= 2025)
                if is_credible and title not in history and s2_id not in history:
                    valid_papers.append({
                        "title": title,
                        "abstract": p.get("abstract", ""),
                        "pdf_url": pdf_url,
                        "authors": [a.get("name") for a in p.get("authors", [])],
                        "year": p.get("year"),
                        "citations": citations,
                        "s2_id": s2_id
                    })


    except Exception as e:
        print(f"⚠️  Semantic Scholar Recommendations API error: {e}")

    if valid_papers:
        # Randomly select one paper from top candidates to guarantee fresh daily recommendations
        selected = random.choice(valid_papers[:10])
        print(f"\n🎯 Selected Fresh Paper: '{selected['title']}' ({selected['year']})")
        print(f"🔗 PDF URL: {selected['pdf_url']}")
        
        # Save selected paper to history to prevent repeat recommendations
        history.add(selected["title"])
        history.add(selected["s2_id"])
        save_history(history)
        
        return selected

    print("⚠️  No unseen paper found in recommendations. Falling back to fresh arXiv search...")
    return fallback_arxiv_search(config, history)

def fallback_arxiv_search(config, history):
    import urllib.request
    import xml.etree.ElementTree as ET
    
    categories = config.get("arxiv_categories", ["cs.AI", "cs.LG"])
    query = " OR ".join([f"cat:{c}" for c in categories])
    encoded_query = urllib.parse.quote(query)
    
    url = f"http://export.arxiv.org/api/query?search_query={encoded_query}&sortBy=submittedDate&sortOrder=descending&max_results=15"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        xml_data = response.read()
        
    root = ET.fromstring(xml_data)
    ns = {'arxiv': 'http://www.w3.org/2005/Atom'}
    
    entries = root.findall('arxiv:entry', ns)
    if not entries:
        raise Exception("Failed to fetch papers from fallback arXiv query.")
        
    unseen_entries = []
    for entry in entries:
        title = entry.find('arxiv:title', ns).text.strip().replace('\n', ' ')
        if title not in history:
            unseen_entries.append(entry)
            
    selected_entry = random.choice(unseen_entries) if unseen_entries else random.choice(entries)
    
    title = selected_entry.find('arxiv:title', ns).text.strip().replace('\n', ' ')
    paper_id = selected_entry.find('arxiv:id', ns).text.split('/')[-1]
    abstract = selected_entry.find('arxiv:summary', ns).text.strip()
    pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
    
    selected = {
        "title": title,
        "abstract": abstract,
        "pdf_url": pdf_url,
        "authors": [],
        "year": 2026,
        "citations": 0,
        "s2_id": f"ARXIV:{paper_id}"
    }
    
    history.add(title)
    history.add(selected["s2_id"])
    save_history(history)
    
    print(f"🎯 Fallback Selected Paper: '{selected['title']}'")
    print(f"🔗 PDF URL: {selected['pdf_url']}")
    return selected

if __name__ == "__main__":
    paper = get_paper_recommendations()
    print("\nSummary:", paper["abstract"][:300], "...")
