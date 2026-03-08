"""YouTube video upload using Data API v3."""

import logging
import os
import random
import time
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_authenticated_service():
    """Build YouTube API service using refresh token from environment."""
    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=credentials)


def upload_video(
    youtube,
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    category_id: str = "22",
    privacy_status: str = "public",
    made_for_kids: bool = False,
) -> str:
    """Upload video to YouTube. Returns the YouTube video ID."""
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:30],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=256 * 1024,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = _resumable_upload(request)
    video_id = response["id"]
    logger.info(f"Uploaded: https://youtube.com/shorts/{video_id}")
    return video_id


def _resumable_upload(request, max_retries: int = 3) -> dict:
    """Execute resumable upload with exponential backoff."""
    response = None
    retry = 0

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                logger.debug(f"Upload {int(status.progress() * 100)}%% complete")
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and retry < max_retries:
                retry += 1
                sleep_seconds = 2 ** retry + random.random()
                logger.warning(
                    f"Upload error {e.resp.status}, retry {retry}/{max_retries} "
                    f"in {sleep_seconds:.1f}s"
                )
                time.sleep(sleep_seconds)
            else:
                raise

    return response
