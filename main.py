"""Instoob: Instagram Reels to YouTube Shorts sync tool."""

import argparse
import logging
import sys

from dotenv import load_dotenv

from src.config import load_config
from src.sync import run_sync


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Instoob - Sync Instagram Reels to YouTube Shorts"
    )
    parser.add_argument(
        "command",
        choices=["sync"],
        help="Command to run",
    )
    parser.add_argument(
        "--config",
        default="config.yml",
        help="Path to config file (default: config.yml)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = load_config(args.config)

    if args.command == "sync":
        count = run_sync(config)
        logger = logging.getLogger(__name__)
        if count > 0:
            logger.info(f"Successfully synced {count} reel(s)")
        sys.exit(0)


if __name__ == "__main__":
    main()
