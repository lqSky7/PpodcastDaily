#!/usr/bin/env python3
"""
podcast_generator.py

Main orchestrator script:
1. Obtains paper recommendation from Semantic Scholar.
2. Restores Google NotebookLM credentials from environment variable.
3. Uploads PDF source to NotebookLM.
4. Requests long-form Audio Overview podcast with custom prompt instructions.
5. Downloads .mp3 podcast output.
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
        # Check if local storage file exists already (for local development)
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
        notebook = await client.create_notebook(title=notebook_title)
        print(f"✅ Created Notebook ID: {notebook.id}")
        
        # 4. Ingest Paper PDF Source
        print(f"📥 Uploading PDF source ({paper['pdf_url']})...")
        await client.source.add_url(notebook.id, paper["pdf_url"], wait=True)
        print("✅ Source successfully ingested into NotebookLM.")
        
        # 5. Send custom podcast generation prompt
        prompt = config.get("podcast_prompt")
        format_type = config.get("podcast_format", "deep-dive")
        
        print("\n🎙️ Triggering Audio Overview podcast generation...")
        print("Prompt instructions:")
        print("--------------------------------------------------")
        print(prompt)
        print("--------------------------------------------------")
        
        audio_job = await client.audio.generate(
            notebook_id=notebook.id,
            prompt=prompt,
            format=format_type,
            wait=True
        )
        
        # 6. Download MP3
        output_dir = pathlib.Path("output")
        output_dir.mkdir(exist_ok=True)
        
        output_mp3 = output_dir / "latest_paper_podcast.mp3"
        print(f"💾 Downloading podcast to {output_mp3}...")
        await client.audio.download(notebook.id, output_path=str(output_mp3))
        
        # Write metadata summary
        info_md = output_dir / "latest_podcast_info.md"
        info_content = f"""# 🎙️ Research Paper Podcast Summary

- **Title:** {paper['title']}
- **Authors:** {', '.join(paper.get('authors', []))} ({paper.get('year')})
- **PDF Source:** [{paper['pdf_url']}]({paper['pdf_url']})
- **Podcast File:** [{output_mp3.name}](file://{output_mp3.resolve()})

## Abstract Overview
{paper.get('abstract', 'No abstract summary available.')}
"""
        info_md.write_text(info_content, encoding="utf-8")
        
        print(f"\n🎉 SUCCESS! Podcast generation complete!")
        print(f"🔊 Audio output saved at: {output_mp3.resolve()}")
        print(f"📄 Summary metadata saved at: {info_md.resolve()}")


def main():
    asyncio.run(run_pipeline())

if __name__ == "__main__":
    main()
