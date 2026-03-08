"""Track synced reels using a JSON file (git-friendly)."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

STATE_FILE = "synced.json"


def load_state(data_dir: str) -> dict:
    """Load state from JSON file."""
    path = Path(data_dir) / STATE_FILE
    if not path.exists():
        return {"synced_reels": [], "last_sync": None}
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.warning(f"Corrupt state file {path}, starting fresh")
        return {"synced_reels": [], "last_sync": None}


def save_state(data_dir: str, state: dict) -> None:
    """Save state to JSON file."""
    path = Path(data_dir) / STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    state["last_sync"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
    logger.info(f"State saved to {path}")


def get_synced_shortcodes(state: dict) -> set[str]:
    """Get set of already-synced reel shortcodes."""
    return {r["shortcode"] for r in state.get("synced_reels", [])}


def add_synced_reel(state: dict, shortcode: str, youtube_id: str, title: str) -> None:
    """Record a successfully synced reel."""
    state.setdefault("synced_reels", []).append({
        "shortcode": shortcode,
        "youtube_id": youtube_id,
        "title": title,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    })
