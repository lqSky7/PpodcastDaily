#!/usr/bin/env python3
"""
podcast_generator.py

Fire-and-Forget NotebookLM Podcast Generator with Self-Healing Auth Sync:
1. Obtains paper recommendation from Semantic Scholar based on seed papers.
2. Restores Google NotebookLM credentials from environment variable.
3. Creates a Notebook and uploads the paper PDF source.
4. Triggers Audio Overview podcast generation with custom instructions (Abstract -> Conclusion -> Methodology).
5. Auto-syncs any refreshed cookies back to GitHub Secrets so credentials never expire!
"""

import os
import pathlib
import asyncio
import subprocess
from paper_recommender import get_paper_recommendations, load_config
from notebooklm import NotebookLMClient

STORAGE_DIR = pathlib.Path.home() / ".notebooklm"
STORAGE_FILE = STORAGE_DIR / "storage_state.json"

DOI_HOST_MARKERS = ("doi.org", "dx.doi.org")

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
        
        # Pass GitHub token if available
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
            print(f"ℹ️  Secret auto-sync skipped (requires secret write permission): {stderr.strip()}")
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
        
        # 4. Ingest source (direct URL first; fallback to NotebookLM research discovery)
        paper_url = paper["pdf_url"]
        use_research_fallback = any(marker in paper_url for marker in DOI_HOST_MARKERS)

        if not use_research_fallback:
            try:
                print(f"📥 Uploading PDF source ({paper_url})...")
                await client.sources.add_url(notebook.id, paper_url, wait=True)
                print("✅ Source successfully ingested into NotebookLM.")
            except Exception as e:
                print(f"⚠️ Direct source ingest failed ({e}). Falling back to NotebookLM web research...")
                use_research_fallback = True
        else:
            print("⚠️ DOI-based source detected; using NotebookLM web research fallback to avoid rate limits.")

        if use_research_fallback:
            authors = ", ".join([a for a in paper.get("authors", []) if a]) or "unknown authors"
            research_query = (
                f'Find reliable web sources for the paper "{paper["title"]}" '
                f'by {authors}. Prioritize the original publication and full-text sources.'
            )
            print("🔎 Starting NotebookLM web research for alternative sources...")
            research_start = await client.research.start(
                notebook_id=notebook.id,
                query=research_query,
                source="web",
                mode="fast"
            )
            research_task = await client.research.wait_for_completion(
                notebook_id=notebook.id,
                task_id=research_start.task_id,
                timeout=180
            )

            if research_task.status.value != "completed" or not research_task.sources:
                raise RuntimeError(
                    f"NotebookLM research fallback failed with status='{research_task.status.value}'."
                )

            await client.research.import_sources_with_verification(
                notebook_id=notebook.id,
                task_id=research_start.task_id,
                sources=research_task.sources,
                max_elapsed=180
            )
            print(f"✅ NotebookLM imported {len(research_task.sources)} researched source(s).")
        
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
