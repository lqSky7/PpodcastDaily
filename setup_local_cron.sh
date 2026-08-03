#!/bin/bash
# setup_local_cron.sh
# Configures a local macOS cron job to automatically extract and sync NotebookLM credentials twice daily (7:00 AM & 7:00 PM IST)

SCRIPT_PATH="/Users/ca5/Documents/antigravity/fearless-newton/sync_auth.py"
PYTHON_PATH="/opt/homebrew/bin/python3"
CRON_JOB="0 7,19 * * * $PYTHON_PATH $SCRIPT_PATH > /tmp/notebooklm_cron_sync.log 2>&1"

# Check if cron job already exists
(crontab -l 2>/dev/null | grep -F "$SCRIPT_PATH") && echo "ℹ️  Local cron job already installed." || (
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "🎉 SUCCESS: Local macOS cron job installed! It will sync your credentials automatically twice daily at 7:00 AM & 7:00 PM."
)
