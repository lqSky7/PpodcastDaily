#!/usr/bin/env python3
"""
podcast_generator.py

Fire-and-Forget NotebookLM Podcast Generator:
1. Obtains paper recommendation from Semantic Scholar based on seed papers.
2. Restores Google NotebookLM credentials from environment variable.
3. Creates a Notebook and uploads the paper PDF source.
4. Triggers Audio Overview podcast generation with custom instructions (Abstract -> Conclusion -> Methodology).
5. Exits immediately so audio synthesizes in the cloud without wasting GitHub Actions runner compute!
"""

import os
import sys
import json
import pathlib
import asyncio
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

async def run_pipeline():
    config = load_config()
    
    # 1. Fetch paper recommendation
    paper = get_paper_recommendations()
    
    # 2. Restore credentials
    restore_session()
    
    # 3. Initialize NotebookLM Client from storage
    async with NotebookLMClient.from_storage() as client:
        notebook_title = f"Paper: {paper['title'][:50]}"
        print(f"\n📘 Creating NotebookLM notebook: '{notebook_title}'...")
        notebook = await client.notebooks.create(title=notebook_title)
        print(f"✅ Created Notebook ID: {notebook.id}")
        
        # 4. Ingest Paper PDF Source
        print(f"📥 Uploading PDF source ({paper['pdf_url']})...")
        await client.sources.add_url(notebook.id, paper["pdf_url"], wait=True)
        print("✅ Source successfully ingested into NotebookLM.")
        
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

def main():
    asyncio.run(run_pipeline())

if __name__ == "__main__":
    main()
