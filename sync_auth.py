#!/usr/bin/env python3
"""
sync_auth.py

Automated macOS Local Cookie Extractor & GitHub Secret Sync Utility.
1. Extracts & decrypts all Google cookies directly from local Chrome / Brave / Edge SQLite database.
2. Formats storage_state.json for NotebookLM.
3. Automatically syncs NOTEBOOKLM_STORAGE_STATE secret to GitHub Actions.
4. Triggers a fresh test workflow run on GitHub.
"""

import os
import sys
import json
import sqlite3
import shutil
import tempfile
import subprocess
import hashlib
from pathlib import Path


STORAGE_PATH = Path.home() / ".notebooklm" / "storage_state.json"
SECRET_NAME = "NOTEBOOKLM_STORAGE_STATE"
REPO_NAME = "lqSky7/PpodcastDaily"

def get_keychain_password(service_name="Chrome Safe Storage"):
    """Fetch encryption password from macOS Keychain."""
    try:
        cmd = ["security", "find-generic-password", "-w", "-s", service_name]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception as e:
        return None

def decrypt_chrome_cookie_value(enc_val, key_hex):
    """Decrypt v10/v11 Chrome AES-128-CBC encrypted cookie value on macOS."""
    if not enc_val or not enc_val.startswith(b"v10"):
        return enc_val.decode("utf-8", errors="ignore") if isinstance(enc_val, bytes) else str(enc_val)
    
    raw_payload = enc_val[3:]
    iv_hex = "20" * 16  # 16 spaces
    
    try:
        proc = subprocess.run(
            ["openssl", "enc", "-d", "-aes-128-cbc", "-K", key_hex, "-iv", iv_hex],
            input=raw_payload,
            capture_output=True
        )
        decrypted = proc.stdout
        if decrypted:
            pad_len = decrypted[-1]
            if 0 < pad_len <= 16:
                decrypted = decrypted[:-pad_len]
            return decrypted.decode("utf-8", errors="ignore")
    except Exception:
        pass
    return ""

def extract_cookies_from_browser():
    """Locate browser cookie DB and extract all Google cookies."""
    possible_paths = [
        ("Chrome", Path.home() / "Library/Application Support/Google/Chrome/Default/Cookies", "Chrome Safe Storage"),
        ("Chrome Profile 1", Path.home() / "Library/Application Support/Google/Chrome/Profile 1/Cookies", "Chrome Safe Storage"),
        ("Brave", Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser/Default/Cookies", "Brave Safe Storage"),
        ("Edge", Path.home() / "Library/Application Support/Microsoft Edge/Default/Cookies", "Microsoft Edge Safe Storage"),
    ]

    target_db = None
    target_service = None
    browser_name = ""

    for bname, p, service in possible_paths:
        if p.exists():
            target_db = p
            target_service = service
            browser_name = bname
            break

    if not target_db:
        print("❌ Could not locate Chrome/Brave/Edge cookies database on this system.")
        return None

    print(f"🔍 Found browser cookies DB: {browser_name} ({target_db})")
    
    key_pass = get_keychain_password(target_service)
    if not key_pass:
        print(f"⚠️  Could not retrieve {target_service} key from macOS Keychain.")
        return None

    # Derive PBKDF2 AES-128 key
    key_bytes = hashlib.pbkdf2_hmac("sha1", key_pass.encode("utf-8"), b"saltysalt", 1003, 16)
    key_hex = key_bytes.hex()

    tmp_db = Path(tempfile.gettempdir()) / "notebooklm_cookies_tmp.db"
    try:
        shutil.copyfile(target_db, tmp_db)
    except PermissionError:
        print("❌ macOS Permission Denied accessing browser cookies DB.")
        print("Grant Full Disk Access to your Terminal in System Settings > Privacy & Security > Full Disk Access.")
        return None

    conn = sqlite3.connect(tmp_db)
    cursor = conn.cursor()

    query = """
        SELECT name, host_key, path, encrypted_value, is_secure, is_httponly, expires_utc 
        FROM cookies 
        WHERE host_key LIKE '%google.com'
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    try:
        tmp_db.unlink()
    except Exception:
        pass

    extracted_cookies = []
    target_cookie_names = {"SID", "HSID", "SSID", "APISID", "SAPISID", "__Secure-1PSID", "__Secure-3PSID", "__Secure-1PSIDTS", "__Secure-3PSIDTS", "SIDCC"}

    for name, host_key, path, enc_val, is_secure, is_httponly, expires_utc in rows:
        if name in target_cookie_names:
            val = decrypt_chrome_cookie_value(enc_val, key_hex)
            if val:
                extracted_cookies.append({
                    "name": name,
                    "value": val,
                    "domain": host_key if host_key.startswith(".") else f".{host_key}",
                    "path": path or "/",
                    "expires": -1,
                    "httpOnly": bool(is_httponly),
                    "secure": bool(is_secure),
                    "sameSite": "Lax"
                })

    print(f"✅ Successfully extracted and decrypted {len(extracted_cookies)} Google authentication cookies!")
    return {
        "cookies": extracted_cookies,
        "origins": [{"origin": "https://notebooklm.google.com", "localStorage": []}]
    }

def sync_to_github(state_data):
    """Sync storage_state.json data directly to GitHub Secrets using gh CLI."""
    json_str = json.dumps(state_data)

    print(f"🚀 Uploading local credentials to GitHub Secret '{SECRET_NAME}'...")
    proc = subprocess.Popen(
        ["gh", "secret", "set", SECRET_NAME, "--repo", REPO_NAME],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=json_str)

    if proc.returncode == 0:
        print("🎉 SUCCESS! Local NotebookLM credentials synced to GitHub Actions Secret!")
        return True
    else:
        print(f"❌ Failed to update GitHub secret: {stderr}")
        return False

def trigger_workflow():
    """Trigger a fresh workflow run on GitHub."""
    print("⚡ Triggering test workflow run on GitHub Actions...")
    res = subprocess.run(["gh", "workflow", "run", "paper_podcast_cron.yml", "--repo", REPO_NAME], capture_output=True, text=True)
    if res.returncode == 0:
        print("🎉 Test workflow run successfully triggered!")
        print("📺 Track progress at: https://github.com/lqSky7/PpodcastDaily/actions")
    else:
        print(f"⚠️  Could not trigger workflow: {res.stderr}")

def main():
    print("=" * 60)
    print("🔒 Automatic Local Cookie Extractor & GitHub Sync")
    print("=" * 60)

    # 1. Extract cookies directly from browser
    state = extract_cookies_from_browser()
    if not state or not state.get("cookies"):
        print("❌ Cookie extraction failed.")
        sys.exit(1)

    # Save to local storage file
    STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"💾 Saved local session state to: {STORAGE_PATH}")

    # 2. Sync to GitHub Secrets
    if sync_to_github(state):
        # 3. Trigger test cron
        trigger_workflow()

if __name__ == "__main__":
    main()
