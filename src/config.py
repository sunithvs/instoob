"""Load configuration from config.yml and environment variables."""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class InstagramConfig:
    username: str = ""
    max_reels_per_run: int = 3
    max_duration: int = 180
    since_date: datetime | None = None  # Only sync reels posted after this date


@dataclass
class YouTubeConfig:
    category_id: str = "22"
    privacy_status: str = "public"
    default_language: str = "en"
    title_prefix: str = ""
    title_suffix: str = ""
    description_suffix: str = "\n\n#Shorts"
    made_for_kids: bool = False


@dataclass
class SyncConfig:
    data_dir: str = "data"
    download_dir: str = "downloads"


@dataclass
class AppConfig:
    instagram: InstagramConfig = field(default_factory=InstagramConfig)
    youtube: YouTubeConfig = field(default_factory=YouTubeConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)


def load_config(config_path: str = "config.yml") -> AppConfig:
    """Load config from YAML file, with env var overrides."""
    config = AppConfig()

    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        ig = data.get("instagram", {})
        since_date = None
        if ig.get("since_date"):
            try:
                since_date = datetime.strptime(str(ig["since_date"]), "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                logger.warning(f"Invalid since_date: {ig['since_date']} (use YYYY-MM-DD)")

        config.instagram = InstagramConfig(
            username=ig.get("username", ""),
            max_reels_per_run=ig.get("max_reels_per_run", 3),
            max_duration=ig.get("max_duration", 180),
            since_date=since_date,
        )

        yt = data.get("youtube", {})
        config.youtube = YouTubeConfig(
            category_id=str(yt.get("category_id", "22")),
            privacy_status=yt.get("privacy_status", "public"),
            default_language=yt.get("default_language", "en"),
            title_prefix=yt.get("title_prefix", ""),
            title_suffix=yt.get("title_suffix", ""),
            description_suffix=yt.get("description_suffix", "\n\n#Shorts"),
            made_for_kids=yt.get("made_for_kids", False),
        )

        sync = data.get("sync", {})
        config.sync = SyncConfig(
            data_dir=sync.get("data_dir", "data"),
            download_dir=sync.get("download_dir", "downloads"),
        )
    else:
        logger.warning(f"Config file {config_path} not found, using defaults")

    # Env var overrides
    if os.environ.get("IG_USERNAME"):
        config.instagram.username = os.environ["IG_USERNAME"]

    return config
