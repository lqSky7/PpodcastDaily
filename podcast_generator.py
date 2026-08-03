#!/usr/bin/env python3
"""
podcast_generator.py

Fire-and-Forget NotebookLM Podcast Generator via Web Research Search:
1. Obtains paper recommendation from Semantic Scholar based on seed papers.
2. Restores Google NotebookLM credentials from environment variable.
3. Creates a Notebook and performs NotebookLM Web Research Search to import sources.
4. Triggers Audio Overview podcast generation with custom instructions (Abstract -> Conclusion -> Methodology).
5. Auto-syncs any refreshed cookies back to GitHub Secrets so credentials never expire!
"""

import os
import sys
import json
import pathlib
import asyncio
import subprocess
from paper_recommender import get_paper_recommendations, load_config
from notebooklm import NotebookLMClient

STORAGE_DIR = pathlib.Path.home() / ".notebooklm"
STORAGE_FILE = STORAGE_DIR / "storage_state.json"

def restore_session():
    """Restore NotebookLM session storage state from environment variable."""
    state_content = os.environ.get("NOTEBOOKLM_STORAGE_STATE")
    if not state_content:
        if STORAGE_FILE.exists():
            print(f"ℹ️  Using existing local storage file: {STORAGE_FILE}")
            return
        raise ValueError("❌ Environment variable NOTEBOOKLM_STORAGE_STATE is missing or empty.")
        
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_FILE.write_text(state_content, encoding="utf-8")
    print(f"✅ NotebookLM credentials restored into {STORAGE_FILE}")

def auto_sync_refreshed_credentials():
    """
    If running in GitHub Actions, sync any updated/refreshed session cookies
    back to GitHub Secrets so login credentials self-heal and never expire.
    """
    if not os.environ.get("GITHUB_ACTIONS"):
        return
        
    if not STORAGE_FILE.exists():
        return
        
    try:
        updated_state = STORAGE_FILE.read_text(encoding="utf-8")
        repo = os.environ.get("GITHUB_REPOSITORY", "lqSky7/PpodcastDaily")
        
        print("🔄 Auto-syncing refreshed NotebookLM session state to GitHub Secrets...")
        proc = subprocess.Popen(
            ["gh", "secret", "set", "NOTEBOOKLM_STORAGE_STATE", "--repo", repo],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input=updated_state)
        
        if proc.returncode == 0:
            print("🎉 SUCCESS: Refreshed session credentials saved back to GitHub Secrets!")
        else:
            print(f"ℹ️  Secret auto-sync skipped: {stderr.strip()}")
    except Exception as e:
        print(f"ℹ️  Secret auto-sync note: {e}")

async def run_pipeline():
    config = load_config()
    
    # 1. Fetch paper recommendation
    paper = get_paper_recommendations()
    
    # 2. Restore credentials
    restore_session()
    
    # 3. Initialize NotebookLM Client from storage (auto-refreshes cookies in flight)
    async with NotebookLMClient.from_storage() as client:
        notebook_title = f"Paper: {paper['title'][:50]}"
        print(f"\n📘 Creating NotebookLM notebook: '{notebook_title}'...")
        notebook = await client.notebooks.create(title=notebook_title)
        print(f"✅ Created Notebook ID: {notebook.id}")
        
        # 4. Perform NotebookLM Web Research Search to ingest sources
        query_str = f"\"{paper['title']}\""
        if paper.get("authors") and paper["authors"][0]:
            query_str += f" {paper['authors'][0]}"
            
        print(f"🔎 Executing NotebookLM Web Research Search for query: {query_str}...")
        start = await client.research.start(notebook.id, query=query_str, source="web", mode="fast")
        task = await client.research.wait_for_completion(notebook.id, start.task_id, timeout=120.0)
        
        if task.sources:
            imported = await client.research.import_sources(notebook.id, start.task_id, sources=task.sources)
            print(f"✅ Successfully imported {len(imported)} Web Research sources into NotebookLM.")
        else:
            # Fallback to direct url ingest if web research yields no items
            print(f"📥 Fallback: Ingesting direct paper URL ({paper['pdf_url']})...")
            await client.sources.add_url(notebook.id, paper["pdf_url"], wait=True)
            print("✅ Direct source ingested into NotebookLM.")
        
        # 5. Send custom podcast generation prompt
        prompt = config.get("podcast_prompt")
        
        print("\n🎙️ Triggering Audio Overview podcast generation...")
        print("Prompt instructions:")
        print("--------------------------------------------------")
        print(prompt)
        print("--------------------------------------------------")
        
        audio_status = await client.artifacts.generate_audio(
            notebook_id=notebook.id,
            instructions=prompt
        )
        
        print(f"\n🎉 SUCCESS! Podcast generation requested in Google NotebookLM!")
        print(f"📌 Task ID: {audio_status.task_id}")
        print(f"🔗 Open your notebook on web: https://notebooklm.google.com/notebook/{notebook.id}")
        print("⚡ Exiting immediately to save GitHub server compute. Audio will render in the cloud!")

    # 6. Auto-sync any refreshed cookies back to GitHub Secrets
    auto_sync_refreshed_credentials()

def main():
    asyncio.run(run_pipeline())

if __name__ == "__main__":
    main()
