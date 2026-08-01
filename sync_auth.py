#!/usr/bin/env python3
"""
sync_auth.py

Automated macOS Local Cookie Extractor & GitHub Secret Sync Utility.
Scans Dia, Chrome, Brave, Edge & Arc browsers for Google session cookies,
decrypts macOS Chromium v10 AES-128-CBC payload (stripping 32-byte header),
formats storage_state.json for NotebookLM, and syncs NOTEBOOKLM_STORAGE_STATE to GitHub.
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

def get_keychain_password(service_names):
    """Fetch encryption password from macOS Keychain trying multiple service names."""
    if isinstance(service_names, str):
        service_names = [service_names]
        
    for s in service_names:
        try:
            cmd = ["security", "find-generic-password", "-w", "-s", s]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            val = res.stdout.strip()
            if val:
                return val
        except Exception:
            continue
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
        if decrypted and len(decrypted) > 32:
            pad_len = decrypted[-1]
            if 0 < pad_len <= 16:
                decrypted = decrypted[:-pad_len]
            # Chromium prepends a 32-byte SHA256 header before actual cookie value
            return decrypted[32:].decode("utf-8", errors="ignore")
    except Exception:
        pass
    return ""

def extract_cookies_from_browser():
    """Locate browser cookie DB and extract all Google cookies."""
    possible_paths = [
        ("Dia Browser", Path.home() / "Library/Application Support/Dia/User Data/Default/Cookies", ["Dia Safe Storage", "Dia"]),
        ("Chrome Default", Path.home() / "Library/Application Support/Google/Chrome/Default/Cookies", ["Chrome Safe Storage", "Chrome"]),
        ("Chrome Profile 1", Path.home() / "Library/Application Support/Google/Chrome/Profile 1/Cookies", ["Chrome Safe Storage", "Chrome"]),
        ("Brave Default", Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser/Default/Cookies", ["Brave Safe Storage", "Brave"]),
        ("Edge Default", Path.home() / "Library/Application Support/Microsoft Edge/Default/Cookies", ["Microsoft Edge Safe Storage", "Microsoft Edge"]),
        ("Arc Default", Path.home() / "Library/Application Support/Arc/User Data/Default/Cookies", ["Arc Safe Storage", "Arc"]),
    ]

    target_cookie_names = {"SID", "HSID", "SSID", "APISID", "SAPISID", "__Secure-1PSID", "__Secure-3PSID", "__Secure-1PSIDTS", "__Secure-3PSIDTS", "SIDCC"}

    for bname, p, services in possible_paths:
        if not p.exists():
            continue

        key_pass = get_keychain_password(services)
        if not key_pass:
            continue

        key_bytes = hashlib.pbkdf2_hmac("sha1", key_pass.encode("utf-8"), b"saltysalt", 1003, 16)
        key_hex = key_bytes.hex()

        tmp_db = Path(tempfile.gettempdir()) / "notebooklm_cookies_scan_tmp.db"
        try:
            shutil.copyfile(p, tmp_db)
        except Exception:
            continue

        try:
            conn = sqlite3.connect(tmp_db)
            cursor = conn.cursor()
            query = """
                SELECT name, host_key, path, encrypted_value, is_secure, is_httponly 
                FROM cookies 
                WHERE host_key LIKE '%google.com'
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            tmp_db.unlink()
        except Exception:
            continue

        extracted_cookies = []
        found_names = set()

        for name, host_key, path, enc_val, is_secure, is_httponly in rows:
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
                        "sameSite": "None" if "3P" in name else "Lax"
                    })
                    found_names.add(name)

        if "SID" in found_names and "__Secure-1PSIDTS" in found_names:
            print(f"🎯 BINGO! Successfully extracted {len(extracted_cookies)} valid Google session cookies from {bname}!")
            return {
                "cookies": extracted_cookies,
                "origins": [{"origin": "https://notebooklm.google.com", "localStorage": []}]
            }

    print("❌ Could not find active Google session cookies with SID & __Secure-1PSIDTS.")
    return None

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

    state = extract_cookies_from_browser()
    if not state or not state.get("cookies"):
        sys.exit(1)

    # Save to local storage file
    STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"💾 Saved local session state to: {STORAGE_PATH}")

    # Sync to GitHub Secrets
    if sync_to_github(state):
        # Trigger test cron
        trigger_workflow()

if __name__ == "__main__":
    main()
