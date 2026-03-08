# Instagram Reels → YouTube Shorts Sync Tool

## Detailed Implementation Plan

---

## The Problem

You're manually downloading your Instagram Reels and re-uploading them to YouTube as Shorts — a repetitive, time-consuming workflow that adds no creative value.

## The Goal

Build a self-hosted automation tool that detects new Reels on your Instagram account and automatically uploads them to your YouTube channel as Shorts, with minimal ongoing maintenance.

---

## Approach Comparison

Before diving into the recommended stack, here's a quick look at the three main approaches and why building your own tool makes sense for your use case.

**Option A: No-code platforms (Repurpose.io, Pabbly, Make.com)**
These work well but come with monthly subscription costs ($15–$50/mo), limited customization, and dependency on a third-party service. If the platform shuts down or changes pricing, you're stuck.

**Option B: Browser automation (Selenium/Playwright)**
Fragile. Instagram and YouTube change their UI frequently, which breaks scrapers. You'd spend more time fixing selectors than creating content.

**Option C: API-first custom tool (Recommended)**
Uses official APIs where possible, well-maintained open-source libraries as fallback, and gives you full control. One-time setup, runs for free on your own machine or a cheap VPS.

---

## Recommended Tech Stack

### Language: Python 3.10+

Python is the natural choice here. It has the best library ecosystem for both Instagram scraping and YouTube API integration, and the automation/scheduling tooling is mature.

### Core Libraries

| Component | Library | Why |
|-----------|---------|-----|
| Instagram download | **Instaloader** (v4.15+) | Most maintained Instagram scraper. Handles login, session management, rate-limiting. Downloads Reels with metadata (caption, hashtags, timestamp). |
| YouTube upload | **google-api-python-client** + **google-auth-oauthlib** | Official Google SDK. Uses `videos.insert` endpoint from YouTube Data API v3. Stable, well-documented. |
| Task scheduling | **APScheduler** or **system cron** | APScheduler for in-process scheduling; cron if you prefer OS-level control. |
| Database | **SQLite** (via `sqlite3` stdlib) | Tracks which Reels have already been synced. Zero config, single file, perfect for this scale. |
| Config management | **python-dotenv** or **TOML** | Store API keys, account credentials, and preferences outside code. |
| CLI interface | **Typer** or **Click** | Optional but nice — lets you run manual syncs, check status, etc. |
| Logging | **loguru** | Clean, structured logging with rotation. Better than stdlib `logging`. |

### Optional Enhancements

| Component | Library | Why |
|-----------|---------|-----|
| Web dashboard | **FastAPI** + **Jinja2** or **Streamlit** | If you want a simple UI to monitor sync status and history. |
| Notification | **apprise** | Send alerts (Telegram, Discord, email) on sync success/failure. |
| Video processing | **FFmpeg** (via subprocess) | Strip Instagram watermarks, adjust aspect ratio, or add intro/outro. |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Scheduler (cron/APScheduler)       │
│                   Runs every 30 min                  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              1. FETCH NEW REELS                      │
│  Instaloader → Check your IG profile for new Reels  │
│  Compare against SQLite DB of already-synced IDs     │
└──────────────────────┬──────────────────────────────┘
                       │ (new Reels found)
                       ▼
┌─────────────────────────────────────────────────────┐
│              2. DOWNLOAD & PROCESS                   │
│  Download video file + metadata (caption, hashtags)  │
│  Optional: FFmpeg to strip watermark / re-encode     │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              3. UPLOAD TO YOUTUBE                     │
│  YouTube Data API v3 → videos.insert                 │
│  Title: IG caption (truncated to 100 chars)          │
│  Description: Full caption + #Shorts                 │
│  Tags: Extracted hashtags                            │
│  Privacy: Public (or unlisted for review)            │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              4. RECORD & NOTIFY                      │
│  Mark Reel as synced in SQLite                       │
│  Send notification (Telegram/Discord/email)          │
│  Clean up temp video files                           │
└─────────────────────────────────────────────────────┘
```

---

## Implementation Plan (Step by Step)

### Phase 1: Project Setup & Authentication (Day 1)

1. **Initialize the project**
   - Create project directory with a clean structure (see below)
   - Set up a virtual environment: `python -m venv venv`
   - Install core dependencies: `pip install instaloader google-api-python-client google-auth-oauthlib python-dotenv loguru typer`

2. **Project structure**
   ```
   reels-to-shorts/
   ├── config/
   │   ├── .env                  # Secrets (gitignored)
   │   └── settings.toml         # Non-secret config
   ├── src/
   │   ├── __init__.py
   │   ├── instagram.py          # Instaloader wrapper
   │   ├── youtube.py            # YouTube API wrapper
   │   ├── database.py           # SQLite operations
   │   ├── processor.py          # Video processing (FFmpeg)
   │   ├── sync.py               # Main orchestration logic
   │   └── notifier.py           # Notifications
   ├── data/
   │   ├── sync.db               # SQLite database
   │   └── downloads/            # Temp video storage
   ├── cli.py                    # CLI entry point
   ├── requirements.txt
   └── README.md
   ```

3. **Set up Instagram authentication**
   - Log into Instaloader with your IG credentials
   - Save the session file so you don't need to re-login each run
   - Test: fetch your latest 3 Reels and verify download

4. **Set up YouTube OAuth 2.0**
   - Create a Google Cloud project at console.cloud.google.com
   - Enable the YouTube Data API v3
   - Create OAuth 2.0 credentials (Desktop app type)
   - Download `client_secrets.json`
   - Run the auth flow once to get a refresh token, save it
   - Test: upload a sample video and verify it appears on your channel

### Phase 2: Core Sync Engine (Day 2–3)

5. **Build the Instagram module** (`src/instagram.py`)
   - Function: `fetch_new_reels(username, since_timestamp) → list[ReelData]`
   - Each `ReelData` contains: shortcode, media_url, caption, hashtags, timestamp, video_path
   - Handle rate limiting with exponential backoff
   - Save session cookies for reuse

6. **Build the database module** (`src/database.py`)
   - SQLite table: `synced_reels (ig_shortcode TEXT PRIMARY KEY, yt_video_id TEXT, synced_at TIMESTAMP, title TEXT, status TEXT)`
   - Functions: `is_synced(shortcode)`, `mark_synced(shortcode, yt_id)`, `get_sync_history()`

7. **Build the YouTube module** (`src/youtube.py`)
   - Function: `upload_short(video_path, title, description, tags, privacy) → yt_video_id`
   - Auto-add `#Shorts` to the description
   - Truncate title to 100 characters
   - Use resumable upload with retry logic
   - Handle quota errors gracefully (1,600 units per upload; default daily quota is 10,000)

8. **Build the sync orchestrator** (`src/sync.py`)
   - Ties everything together:
     1. Fetch new Reels
     2. Filter out already-synced ones
     3. Download each new Reel
     4. Optionally process with FFmpeg
     5. Upload to YouTube
     6. Mark as synced
     7. Clean up temp files
   - Process Reels in chronological order (oldest first)

### Phase 3: Scheduling & Polish (Day 4)

9. **Add scheduling**
   - Option A (simple): Use system cron — `*/30 * * * * cd /path/to/project && python cli.py sync`
   - Option B (in-app): Use APScheduler with a configurable interval
   - Default: check every 30 minutes

10. **Add CLI commands** (`cli.py`)
    - `sync` — Run a sync cycle manually
    - `status` — Show last sync time, pending Reels, quota usage
    - `history` — Show all synced Reels with YouTube links
    - `auth` — Re-authenticate Instagram or YouTube

11. **Add notifications** (`src/notifier.py`)
    - Use `apprise` library for multi-platform notifications
    - Notify on: successful sync, failed upload, quota exhaustion
    - Configurable via `.env` (Telegram bot token, Discord webhook, etc.)

12. **Add video processing** (`src/processor.py`)
    - Optional FFmpeg pipeline: remove watermark, normalize audio, re-encode for YouTube
    - Keep it optional — raw Reels already work fine as Shorts

### Phase 4: Deployment (Day 5)

13. **Choose where to run it**
    - **Local machine**: Simplest. Use cron or a background service.
    - **Cheap VPS** ($5/mo DigitalOcean, Hetzner): Runs 24/7 without your laptop being on.
    - **Raspberry Pi**: Free after hardware cost, runs at home.
    - **Docker**: Wrap in a container for easy deployment anywhere.

14. **Dockerize (optional but recommended)**
    ```dockerfile
    FROM python:3.11-slim
    RUN apt-get update && apt-get install -y ffmpeg
    COPY requirements.txt .
    RUN pip install -r requirements.txt
    COPY . /app
    WORKDIR /app
    CMD ["python", "cli.py", "sync", "--loop"]
    ```

---

## Key Gotchas & Things to Watch Out For

**YouTube API quotas**: You get 10,000 units/day by default. Each upload costs 1,600 units, so you can upload about 6 videos per day. If you post more Reels than that, you'll need to request a quota increase from Google.

**Instagram rate limiting**: Instaloader respects rate limits, but if you poll too aggressively, Instagram may temporarily block your session. Stick to checking every 30 minutes and you'll be fine.

**Instagram login sessions expire**: Save and reuse session files. If a session expires, you'll need to re-authenticate (Instaloader handles this, but you should monitor for auth failures).

**YouTube #Shorts detection**: For YouTube to recognize a video as a Short, it must be 60 seconds or less AND have `#Shorts` in the title or description. Most Reels are under 90 seconds, but double-check — Reels over 60s won't be treated as Shorts.

**Copyright/music**: Instagram Reels often use licensed music that may trigger Content ID claims on YouTube. Consider stripping audio or replacing it with royalty-free music via FFmpeg if this is a concern.

**Watermarks**: Downloaded Reels may have Instagram watermarks. FFmpeg can crop them out, but this requires knowing the exact watermark position, which can vary.

---

## Estimated Timeline

| Phase | Work | Time |
|-------|------|------|
| Phase 1 | Setup + auth | 1 day |
| Phase 2 | Core sync engine | 2 days |
| Phase 3 | Scheduling, CLI, notifications | 1 day |
| Phase 4 | Deployment + Docker | 1 day |
| **Total** | | **~5 days** |

---

## Quick-Start Checklist

- [ ] Create Google Cloud project + enable YouTube Data API v3
- [ ] Set up OAuth 2.0 credentials (Desktop app type)
- [ ] Install Python 3.10+ and create virtual environment
- [ ] Install Instaloader and test downloading your own Reels
- [ ] Run YouTube auth flow and test uploading a sample video
- [ ] Build the sync engine connecting both
- [ ] Set up cron/scheduler
- [ ] Deploy and monitor
