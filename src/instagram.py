"""Instagram reel fetching and downloading.

Uses Instagram's private API with a session cookie for reel discovery,
and yt-dlp for reliable video downloads. No password or 2FA needed -
just a sessionid cookie from your browser.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

import requests

logger = logging.getLogger(__name__)

# Instagram's web app ID (public, used by the web frontend)
IG_APP_ID = "936619743392459"


@dataclass
class ReelInfo:
    shortcode: str
    caption: str
    hashtags: list[str]
    video_url: str
    duration: float
    date: datetime


def _get_session() -> requests.Session:
    """Create a requests session with Instagram auth cookies."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "X-IG-App-ID": IG_APP_ID,
    })

    session_id = _get_session_id()
    if session_id:
        session.cookies.set("sessionid", session_id, domain=".instagram.com")
        # Generate a basic CSRF token
        csrf = session_id[:32] if len(session_id) >= 32 else session_id
        session.cookies.set("csrftoken", csrf, domain=".instagram.com")
        session.headers["X-CSRFToken"] = csrf

    return session


def _get_session_id() -> str | None:
    """Get Instagram session ID from available auth sources."""
    # 1. IG_SESSION_ID (simplest - just paste the cookie value)
    session_id = os.environ.get("IG_SESSION_ID")
    if session_id:
        logger.info("Using IG_SESSION_ID")
        return unquote(session_id)

    # 2. IG_SESSION_BASE64 (backward compat with old instaloader format)
    session_b64 = os.environ.get("IG_SESSION_BASE64")
    if session_b64:
        try:
            import base64
            import pickle
            data = pickle.loads(base64.b64decode(session_b64))
            if isinstance(data, dict) and "sessionid" in data:
                logger.info("Extracted sessionid from IG_SESSION_BASE64")
                return unquote(data["sessionid"])
        except Exception:
            logger.warning("Failed to extract sessionid from IG_SESSION_BASE64")

    logger.warning("No Instagram session configured. Set IG_SESSION_ID in your secrets.")
    return None


def _get_user_id(session: requests.Session, username: str) -> str | None:
    """Get user ID from username."""
    url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
    try:
        r = session.get(url, timeout=15)
        r.raise_for_status()
        return r.json()["data"]["user"]["id"]
    except Exception:
        logger.exception(f"Failed to get user ID for @{username}")
        return None


def fetch_reels(
    username: str,
    max_count: int,
    max_duration: int,
    already_synced: set[str],
    since_date: datetime | None = None,
) -> list[ReelInfo]:
    """Fetch reels from a profile using Instagram's API."""
    if since_date:
        logger.info(f"Fetching reels from @{username} since {since_date.date()}...")
    else:
        logger.info(f"Fetching reels from @{username}...")

    session = _get_session()

    # Get user ID
    user_id = _get_user_id(session, username)
    if not user_id:
        return []

    # Fetch reels via clips/user endpoint
    reels = []
    max_id = None
    pages = 0

    while len(reels) < max_count and pages < 5:
        data = {"target_user_id": user_id, "page_size": 12}
        if max_id:
            data["max_id"] = max_id

        try:
            r = session.post(
                "https://i.instagram.com/api/v1/clips/user/",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15,
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 429:
                logger.warning("Rate limited by Instagram. Try again later.")
            else:
                logger.error(f"Instagram API error: {e}")
            break
        except Exception:
            logger.exception("Failed to fetch reels")
            break

        result = r.json()
        items = result.get("items", [])
        if not items:
            break

        for item in items:
            media = item.get("media", {})
            shortcode = media.get("code", "")
            if not shortcode:
                continue

            if shortcode in already_synced:
                logger.debug(f"Skipping {shortcode}: already synced")
                continue

            # Parse date
            taken_at = media.get("taken_at", 0)
            post_date = datetime.fromtimestamp(taken_at, tz=timezone.utc) if taken_at else datetime.now(timezone.utc)

            if since_date and post_date < since_date:
                logger.debug(f"Skipping {shortcode}: before since_date")
                continue

            duration = media.get("video_duration", 0) or 0
            if max_duration > 0 and duration > max_duration:
                logger.debug(f"Skipping {shortcode}: {duration:.0f}s > {max_duration}s")
                continue

            caption_obj = media.get("caption")
            caption = caption_obj.get("text", "") if caption_obj else ""
            hashtags = [w.lstrip("#") for w in caption.split() if w.startswith("#")]

            # Get video URL from video_versions
            video_versions = media.get("video_versions", [])
            video_url = video_versions[0]["url"] if video_versions else ""

            reels.append(ReelInfo(
                shortcode=shortcode,
                caption=caption,
                hashtags=hashtags,
                video_url=video_url,
                duration=duration,
                date=post_date,
            ))

            if len(reels) >= max_count:
                break

        # Pagination
        paging = result.get("paging_info", {})
        if not paging.get("more_available"):
            break
        max_id = paging.get("max_id")
        pages += 1

    # Process oldest first
    reels.sort(key=lambda r: r.date)
    logger.info(f"Found {len(reels)} new reels")
    return reels


def download_reel(reel: ReelInfo, download_dir: Path) -> Path:
    """Download a reel video. Tries direct URL first, falls back to yt-dlp."""
    download_dir.mkdir(parents=True, exist_ok=True)
    video_path = download_dir / f"{reel.shortcode}.mp4"

    # Try direct download from video_url (fastest, no external tool needed)
    if reel.video_url and reel.video_url.startswith("http"):
        try:
            logger.info(f"Downloading {reel.shortcode} (direct)...")
            resp = requests.get(reel.video_url, stream=True, timeout=120, headers={
                "User-Agent": "Mozilla/5.0",
            })
            resp.raise_for_status()

            with open(video_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            if video_path.exists() and video_path.stat().st_size > 1000:
                size_mb = video_path.stat().st_size / 1024 / 1024
                logger.info(f"Downloaded {video_path.name} ({size_mb:.1f} MB)")
                return video_path

            # File too small, likely an error page
            video_path.unlink(missing_ok=True)
            logger.warning(f"Direct download too small, trying yt-dlp...")
        except Exception as e:
            logger.warning(f"Direct download failed ({e}), trying yt-dlp...")
            video_path.unlink(missing_ok=True)

    # Fallback to yt-dlp
    return _download_with_ytdlp(reel, video_path, download_dir)


def _ytdlp_cmd() -> list[str]:
    """Return the yt-dlp command."""
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    return [sys.executable, "-m", "yt_dlp"]


def _get_cookies_file() -> str | None:
    """Create a Netscape cookies.txt file for yt-dlp."""
    session_id = _get_session_id()
    if not session_id:
        return None

    cookies_path = Path(tempfile.gettempdir()) / "ig_cookies.txt"
    cookies_content = (
        "# Netscape HTTP Cookie File\n"
        f".instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\t{session_id}\n"
    )
    cookies_path.write_text(cookies_content)
    return str(cookies_path)


def _download_with_ytdlp(reel: ReelInfo, video_path: Path, download_dir: Path) -> Path:
    """Download a reel using yt-dlp."""
    reel_url = f"https://www.instagram.com/reel/{reel.shortcode}/"
    logger.info(f"Downloading {reel.shortcode} via yt-dlp...")

    cookies_file = _get_cookies_file()
    cookies_args = ["--cookies", cookies_file] if cookies_file else []

    cmd = _ytdlp_cmd() + cookies_args + [
        "-o", str(video_path),
        "--no-warnings",
        "--merge-output-format", "mp4",
        reel_url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        logger.error(f"Download timed out for {reel.shortcode}")
        raise
    except FileNotFoundError:
        logger.error("yt-dlp not found. Install it: pip install yt-dlp")
        raise

    if result.returncode != 0:
        logger.error(f"yt-dlp download failed: {result.stderr.strip()}")
        raise RuntimeError(f"Failed to download reel {reel.shortcode}")

    # yt-dlp might add extension, find the actual file
    if not video_path.exists():
        for candidate in download_dir.glob(f"{reel.shortcode}.*"):
            if candidate.suffix in (".mp4", ".webm", ".mkv"):
                video_path = candidate
                break

    if not video_path.exists():
        raise FileNotFoundError(f"Downloaded file not found for {reel.shortcode}")

    size_mb = video_path.stat().st_size / 1024 / 1024
    logger.info(f"Downloaded {video_path.name} ({size_mb:.1f} MB)")
    return video_path
