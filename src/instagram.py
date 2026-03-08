"""Instagram reel fetching and downloading using Instaloader."""

import base64
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import instaloader
import requests

logger = logging.getLogger(__name__)


@dataclass
class ReelInfo:
    shortcode: str
    caption: str
    hashtags: list[str]
    video_url: str
    duration: float
    date: datetime


def create_loader(quiet: bool = True) -> instaloader.Instaloader:
    """Create an Instaloader instance configured for reel downloads."""
    return instaloader.Instaloader(
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        post_metadata_txt_pattern="",
        quiet=quiet,
    )


def login(loader: instaloader.Instaloader, username: str) -> None:
    """Log into Instagram using available credentials (env vars or local session)."""
    # 1. Try IG_PASSWORD env var (simplest for GitHub Actions)
    password = os.environ.get("IG_PASSWORD")
    if password:
        try:
            loader.login(username, password)
            logger.info(f"Logged in as {username} via password")
            return
        except instaloader.TwoFactorAuthRequiredException:
            logger.error(
                "2FA is enabled on this account. Either disable 2FA or use "
                "IG_SESSION_BASE64 instead (see README)."
            )
            raise
        except Exception:
            logger.exception("Login with password failed")
            raise

    # 2. Try IG_SESSION_BASE64 env var (for 2FA accounts)
    session_b64 = os.environ.get("IG_SESSION_BASE64")
    if session_b64:
        try:
            session_bytes = base64.b64decode(session_b64)
            session_path = Path(tempfile.gettempdir()) / f"ig_session_{username}"
            session_path.write_bytes(session_bytes)
            loader.load_session_from_file(username, filename=str(session_path))
            logger.info(f"Session loaded from IG_SESSION_BASE64")
            return
        except Exception:
            logger.exception("Failed to load session from IG_SESSION_BASE64")
            raise

    # 3. Try local session file (for local development)
    default_path = Path.home() / ".config" / "instaloader" / f"session-{username}"
    if default_path.exists():
        try:
            loader.load_session_from_file(username, filename=str(default_path))
            logger.info(f"Session loaded from {default_path}")
            return
        except Exception:
            logger.warning(f"Failed to load session from {default_path}")

    # 4. No auth - will work with retries but less reliable
    logger.warning("No Instagram credentials found. Running without authentication.")


def fetch_reels(
    loader: instaloader.Instaloader,
    username: str,
    max_count: int,
    max_duration: int,
    already_synced: set[str],
    since_date: datetime | None = None,
) -> list[ReelInfo]:
    """Fetch reels from a profile, filtering by duration, date, and sync status."""
    profile = instaloader.Profile.from_username(loader.context, username)
    reels = []

    if since_date:
        logger.info(f"Fetching reels from @{username} since {since_date.date()}...")
    else:
        logger.info(f"Fetching reels from @{username}...")

    for post in profile.get_posts():
        # Posts are returned newest-first; stop early if we've passed since_date
        post_date = post.date_utc.replace(tzinfo=timezone.utc) if post.date_utc.tzinfo is None else post.date_utc
        if since_date and post_date < since_date:
            logger.debug(f"Reached posts before {since_date.date()}, stopping")
            break

        if not post.is_video:
            continue
        # Filter for reels (typename check)
        if post.typename not in ("GraphVideo", "XDTGraphVideo"):
            continue

        if post.shortcode in already_synced:
            logger.debug(f"Skipping {post.shortcode}: already synced")
            continue

        duration = post.video_duration or 0
        if max_duration > 0 and duration > max_duration:
            logger.debug(f"Skipping {post.shortcode}: {duration}s > {max_duration}s")
            continue

        reels.append(ReelInfo(
            shortcode=post.shortcode,
            caption=post.caption or "",
            hashtags=post.caption_hashtags or [],
            video_url=post.video_url,
            duration=duration,
            date=post.date_utc,
        ))

        if len(reels) >= max_count:
            break

    # Process oldest first
    reels.sort(key=lambda r: r.date)
    return reels


def download_reel(reel: ReelInfo, download_dir: Path) -> Path:
    """Download a reel video directly from its URL. Returns path to the .mp4 file."""
    download_dir.mkdir(parents=True, exist_ok=True)
    video_path = download_dir / f"{reel.shortcode}.mp4"

    logger.info(f"Downloading {reel.shortcode}...")
    resp = requests.get(reel.video_url, stream=True, timeout=120)
    resp.raise_for_status()

    with open(video_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info(f"Downloaded {video_path} ({video_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return video_path
