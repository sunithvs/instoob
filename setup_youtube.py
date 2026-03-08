"""
One-time YouTube OAuth setup.

Run locally:
    python setup_youtube.py

Prerequisites:
    1. Create a Google Cloud project at https://console.cloud.google.com
    2. Enable the YouTube Data API v3
    3. Create OAuth 2.0 credentials (Desktop app type)
    4. Download the JSON and save as client_secrets.json in this directory

This script will open a browser for Google OAuth consent and print
the credentials you need to store as GitHub Secrets or in .env.
"""

import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS_FILE = "client_secrets.json"


def main():
    print("=== Instoob YouTube Setup ===\n")

    if not Path(CLIENT_SECRETS_FILE).exists():
        print(f"ERROR: {CLIENT_SECRETS_FILE} not found in current directory.")
        print()
        print("To get this file:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. Create a project (or select existing)")
        print("  3. Enable 'YouTube Data API v3'")
        print("  4. Go to Credentials > Create Credentials > OAuth client ID")
        print("  5. Application type: Desktop app")
        print("  6. Download the JSON file")
        print(f"  7. Save it as {CLIENT_SECRETS_FILE} here")
        sys.exit(1)

    print("Opening browser for Google OAuth consent...\n")

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_local_server(
        port=8080,
        prompt="consent",
        access_type="offline",
    )

    with open(CLIENT_SECRETS_FILE) as f:
        client_config = json.load(f)

    installed = client_config.get("installed", client_config.get("web", {}))

    print("\n=== Setup Complete ===\n")
    print("Add these as GitHub Secrets (Settings > Secrets > Actions):")
    print("Or add them to your .env file for local use:\n")
    print(f"  YOUTUBE_CLIENT_ID={installed['client_id']}")
    print(f"  YOUTUBE_CLIENT_SECRET={installed['client_secret']}")
    print(f"  YOUTUBE_REFRESH_TOKEN={credentials.refresh_token}")
    print()


if __name__ == "__main__":
    main()
