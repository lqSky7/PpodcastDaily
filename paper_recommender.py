#!/usr/bin/env python3
"""
paper_recommender.py

Interfaces with Semantic Scholar Recommendations API to discover recommended
research papers based on seed papers and interest categories.
"""

import json
import pathlib
import requests
import random

CONFIG_PATH = pathlib.Path(__file__).parent / "config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_paper_recommendations(limit=10):
    config = load_config()
    seed_papers = config.get("seed_papers", [])
    
    # Extract IDs (ArXiv IDs, DOIs, etc.)
    seed_ids = []
    for paper in seed_papers:
        if "id" in paper:
            seed_ids.append(paper["id"])
            
    print(f"🔍 Querying Semantic Scholar Recommendations with {len(seed_ids)} seed papers...")
    
    url = "https://api.semanticscholar.org/recommendations/v1/papers/"
    payload = {
        "positivePaperIds": seed_ids,
        "negativePaperIds": []
    }
    params = {
        "fields": "title,abstract,authors,year,externalIds,openAccessPdf,citationCount,venue",
        "limit": limit
    }
    
    headers = {"User-Agent": "NotebookLM-Podcast-Bot/1.0"}
    
    try:
        res = requests.post(url, json=payload, params=params, headers=headers, timeout=15)
        res.raise_for_status()
        data = res.json()
        recommendations = data.get("recommendedPapers", [])
        print(f"✅ Semantic Scholar returned {len(recommendations)} recommended papers.")
    except Exception as e:
        print(f"⚠️  Semantic Scholar Recommendations API call failed/timed out: {e}")
        recommendations = []

    # Filter papers with valid open access PDF URLs
    valid_papers = []
    for p in recommendations:
        oa_pdf = p.get("openAccessPdf")
        external_ids = p.get("externalIds", {})
        
        pdf_url = None
        if oa_pdf and oa_pdf.get("url"):
            pdf_url = oa_pdf["url"]
        elif external_ids.get("ArXiv"):
            pdf_url = f"https://arxiv.org/pdf/{external_ids['ArXiv']}.pdf"

        if pdf_url:
            valid_papers.append({
                "title": p.get("title", "Untitled Paper"),
                "abstract": p.get("abstract", ""),
                "pdf_url": pdf_url,
                "authors": [a.get("name") for a in p.get("authors", [])],
                "year": p.get("year"),
                "citations": p.get("citationCount", 0),
                "s2_id": p.get("paperId")
            })

    if valid_papers:
        # Select top recommended paper
        selected = valid_papers[0]
        print(f"\n🎯 Selected Paper: '{selected['title']}' ({selected['year']})")
        print(f"🔗 PDF URL: {selected['pdf_url']}")
        return selected

    print("⚠️  No paper with accessible PDF found in direct recommendations. Falling back to arXiv feed search...")
    return fallback_arxiv_search(config)

def fallback_arxiv_search(config):
    import urllib.request
    import xml.etree.ElementTree as ET
    
    categories = config.get("arxiv_categories", ["cs.AI", "cs.LG"])
    query = " OR ".join([f"cat:{c}" for c in categories])
    encoded_query = urllib.parse.quote(query)
    
    url = f"http://export.arxiv.org/api/query?search_query={encoded_query}&sortBy=submittedDate&sortOrder=descending&max_results=5"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        xml_data = response.read()
        
    root = ET.fromstring(xml_data)
    ns = {'arxiv': 'http://www.w3.org/2005/Atom'}
    
    entries = root.findall('arxiv:entry', ns)
    if not entries:
        raise Exception("Failed to fetch papers from fallback arXiv query.")
        
    entry = random.choice(entries)
    title = entry.find('arxiv:title', ns).text.strip().replace('\n', ' ')
    paper_id = entry.find('arxiv:id', ns).text.split('/')[-1]
    abstract = entry.find('arxiv:summary', ns).text.strip()
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
    print(f"🎯 Fallback Selected Paper: '{selected['title']}'")
    print(f"🔗 PDF URL: {selected['pdf_url']}")
    return selected

if __name__ == "__main__":
    paper = get_paper_recommendations()
    print("\nSummary:", paper["abstract"][:300], "...")
