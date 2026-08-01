#!/usr/bin/env python3
"""
sync_auth.py

Local CLI tool to login to Google NotebookLM and automatically sync session credentials
(storage_state.json) directly to GitHub Actions Secrets.
"""

import os
import sys
import json
import subprocess
import pathlib

STORAGE_PATH = pathlib.Path.home() / ".notebooklm" / "storage_state.json"
SECRET_NAME = "NOTEBOOKLM_STORAGE_STATE"

def check_login():
    """Ensure local login state exists."""
    if not STORAGE_PATH.exists():
        print("🔑 Local session state not found. Launching NotebookLM login...")
        try:
            subprocess.run(["notebooklm", "login"], check=True)
        except Exception as e:
            print(f"❌ Login failed or 'notebooklm' command not in PATH: {e}")
            print("Please run 'pip install notebooklm-py[browser]' and 'notebooklm login' manually.")
            sys.exit(1)
    else:
        print(f"✅ Found existing local credentials at: {STORAGE_PATH}")

def sync_to_github():
    """Sync storage_state.json to GitHub Secrets using GitHub CLI (gh)."""
    with open(STORAGE_PATH, "r", encoding="utf-8") as f:
        credentials_json = f.read()

    # Check if gh CLI is installed
    try:
        res = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        if res.returncode != 0:
            print("⚠️  GitHub CLI ('gh') is not logged in. Please run 'gh auth login' first.")
            sys.exit(1)
    except FileNotFoundError:
        print("❌ GitHub CLI ('gh') is not installed on your system.")
        print("Install it from https://cli.github.com/ or set secret manually.")
        sys.exit(1)

    print(f"🚀 Uploading local credentials to GitHub Secret '{SECRET_NAME}'...")
    
    # Pipe credentials into gh secret set
    proc = subprocess.Popen(
        ["gh", "secret", "set", SECRET_NAME],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=credentials_json)

    if proc.returncode == 0:
        print("🎉 SUCCESS! Local NotebookLM credentials synced to GitHub Actions Secret!")
    else:
        print(f"❌ Failed to update secret: {stderr}")
        sys.exit(1)

def main():
    print("=" * 60)
    print("🔒 NotebookLM -> GitHub Secret Auto-Sync Utility")
    print("=" * 60)
    
    if "--force-login" in sys.argv:
        print("🔄 Force login requested...")
        subprocess.run(["notebooklm", "login"], check=True)
        
    check_login()
    sync_to_github()

if __name__ == "__main__":
    main()
