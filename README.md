# Instoob

Automatically sync your Instagram Reels to YouTube Shorts.

Runs on GitHub Actions (scheduled) or locally. Fork-friendly: just update config and secrets.

## Quick Start (Fork & Go)

1. **Fork** this repository
2. **Edit** `config.yml` — set your Instagram username
3. **Set up YouTube API** (see below) — get your OAuth credentials
4. **Add GitHub Secrets** — add the secrets to your fork (see table below)
5. **Enable Actions** — go to Actions tab and enable workflows
6. **Run** — trigger manually or wait for the next scheduled run

## GitHub Secrets Required

Add these in your fork: **Settings > Secrets and variables > Actions > New repository secret**

| Secret | Required | Description |
|--------|----------|-------------|
| `YOUTUBE_CLIENT_ID` | Yes | Google OAuth client ID |
| `YOUTUBE_CLIENT_SECRET` | Yes | Google OAuth client secret |
| `YOUTUBE_REFRESH_TOKEN` | Yes | YouTube refresh token |
| `IG_PASSWORD` | Pick one | Instagram password (simplest, no 2FA) |
| `IG_SESSION_BASE64` | Pick one | Base64 session cookie (for 2FA accounts) |

For Instagram auth, use **either** `IG_PASSWORD` or `IG_SESSION_BASE64` — not both needed.

## YouTube API Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (e.g., "Instoob")
3. Go to **APIs & Services > Library**
4. Search for **YouTube Data API v3** and enable it

### 2. Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - User type: **External**
   - App name: "Instoob"
   - Add your email as a test user
4. Application type: **Desktop app**
5. Download the JSON file and save as `client_secrets.json` in the project root

### 3. Get Your Refresh Token

```bash
pip install -r requirements.txt
python setup_youtube.py
```

A browser window opens — sign in with the Google account that owns your YouTube channel and grant permission. The script prints your credentials.

> **Note**: While your Google Cloud project is in "Testing" mode, refresh tokens expire every 7 days. To avoid this, go to OAuth consent screen and click "Publish App".

## Instagram Auth Setup

Pick one method:

### Option 1: Password (simplest)

Just add your Instagram password as the `IG_PASSWORD` GitHub Secret. That's it — the tool logs in automatically on every run.

> **Note**: This won't work if you have 2FA enabled. Use Option 2 instead.

### Option 2: Session Cookie (for 2FA accounts)

```bash
pip install instaloader
instaloader --login YOUR_INSTAGRAM_USERNAME
base64 -i ~/.config/instaloader/session-YOUR_INSTAGRAM_USERNAME
```

Copy the base64 output and add it as the `IG_SESSION_BASE64` GitHub Secret.

> **Note**: Sessions can expire after a few months. Re-run these steps if sync fails with an auth error.

## Configuration

Edit `config.yml` to customize:

```yaml
instagram:
  username: "your_username"    # Instagram profile to sync from
  max_reels_per_run: 3         # Max reels per sync cycle
  max_duration: 180            # Skip reels longer than this (seconds)

youtube:
  privacy_status: "public"     # public | unlisted | private
  category_id: "22"            # YouTube category
  description_suffix: "\n\n#Shorts"
  made_for_kids: false

sync:
  data_dir: "data"
  download_dir: "downloads"
```

## Running Locally

```bash
# Set up environment
cp .env.example .env
# Fill in your credentials in .env

# Run sync
python main.py sync

# Verbose output
python main.py sync --verbose
```

## How It Works

1. Fetches recent video posts from the configured Instagram profile
2. Filters out already-synced reels (tracked in `data/synced.json`)
3. Downloads new reel videos
4. Uploads each to YouTube as a Short with caption and hashtags
5. Records synced reels to prevent duplicates
6. On GitHub Actions: commits state back to the repository

## Schedule

The GitHub Actions workflow runs every 6 hours by default. Edit `.github/workflows/sync.yml` to change the cron schedule:

```yaml
schedule:
  - cron: "0 */6 * * *"  # Every 6 hours
  # - cron: "0 */12 * * *"  # Every 12 hours
  # - cron: "0 9 * * *"     # Daily at 9 AM UTC
```

## YouTube API Quotas

- Default quota: 10,000 units/day
- Each upload costs ~1,600 units
- That's roughly **6 uploads per day**
- With `max_reels_per_run: 3` and 4 runs/day = 12 reels max (may hit quota)
- Adjust `max_reels_per_run` or schedule frequency if needed

## Troubleshooting

**Instagram auth failed**: If using password, check `IG_PASSWORD` is correct. If using session, re-generate `IG_SESSION_BASE64`.

**YouTube auth error**: Re-run `python setup_youtube.py` to get a new refresh token.

**Quota exceeded**: Reduce `max_reels_per_run` in config.yml or reduce schedule frequency.

**No reels found**: Check that the Instagram username is correct and the profile has public video posts.
