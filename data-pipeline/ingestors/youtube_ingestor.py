"""
YouTube Ingestor
================
For every game in the `games` table, searches YouTube for a gameplay video
and stores the result in `youtube_videos`.

API used: YouTube Data API v3 (requires YOUTUBE_API_KEY in .env)
  - search.list  : 100 quota units/call  → finds the best gameplay video
  - videos.list  :   1 quota unit/call   → fetches view/like counts

Daily quota: 10,000 units free.
  50 games  →  5,000 units  (safe)
  100 games → 10,000 units  (hits daily limit — spread over 2 days)

Run:
    python -m ingestors.youtube_ingestor              # all games in DB
    python -m ingestors.youtube_ingestor --dry-run    # print JSON, no DB write
    python -m ingestors.youtube_ingestor --limit 5    # only 5 games
    python -m ingestors.youtube_ingestor --force      # re-fetch even if video exists
"""

import argparse
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ingestors.utils import db_cursor, rate_sleep

load_dotenv()
logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
SEARCH_QUERY    = "{game_name} gameplay"   # query template


# ──────────────────────────────────────────────
# YouTube API client
# ──────────────────────────────────────────────

def get_youtube_client():
    """Build and return a YouTube Data API v3 client."""
    if not YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY is not set in .env")
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


# ──────────────────────────────────────────────
# Fetch helpers
# ──────────────────────────────────────────────

def search_gameplay_video(youtube, game_name: str) -> Optional[dict]:
    """
    Search YouTube for '{game_name} gameplay' and return the top video's
    basic info (video_id, title, channel, thumbnail, published_at).
    Costs 100 quota units.
    """
    query = SEARCH_QUERY.format(game_name=game_name)
    try:
        response = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=1,
            order="relevance",
            videoEmbeddable="true",  # only embeddable videos
            safeSearch="moderate",
        ).execute()

        items = response.get("items", [])
        if not items:
            logger.warning("No YouTube results for: '%s'", query)
            return None

        item = items[0]
        snippet = item["snippet"]
        video_id = item["id"]["videoId"]

        return {
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "thumbnail_url": (
                snippet.get("thumbnails", {})
                .get("high", {})
                .get("url", "")
                or snippet.get("thumbnails", {})
                .get("default", {})
                .get("url", "")
            ),
            "published_at": snippet.get("publishedAt"),
        }
    except HttpError as exc:
        logger.error("YouTube search failed for '%s': %s", game_name, exc)
        return None


def fetch_video_stats(youtube, video_id: str) -> dict:
    """
    Fetch view and like counts for a video_id.
    Costs 1 quota unit.
    """
    try:
        response = youtube.videos().list(
            id=video_id,
            part="statistics",
        ).execute()

        items = response.get("items", [])
        if not items:
            return {"view_count": 0, "like_count": 0}

        stats = items[0].get("statistics", {})
        return {
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
        }
    except HttpError as exc:
        logger.error("YouTube stats failed for video_id=%s: %s", video_id, exc)
        return {"view_count": 0, "like_count": 0}


# ──────────────────────────────────────────────
# DB helpers
# ──────────────────────────────────────────────

def load_games(limit: Optional[int] = None, force: bool = False) -> list[dict]:
    """
    Load games from DB that need a YouTube video.
    If force=False, skip games that already have a video.
    """
    if force:
        sql = "SELECT id, name FROM games ORDER BY id LIMIT %(limit)s"
    else:
        sql = """
            SELECT g.id, g.name
            FROM games g
            LEFT JOIN youtube_videos yv ON yv.app_id = g.id
            WHERE yv.id IS NULL
            ORDER BY g.id
            LIMIT %(limit)s
        """
    limit_val = limit if limit else 10_000
    with db_cursor() as cur:
        cur.execute(sql, {"limit": limit_val})
        return [dict(row) for row in cur.fetchall()]


UPSERT_VIDEO_SQL = """
INSERT INTO youtube_videos (
    app_id, video_id, title, channel_title,
    thumbnail_url, published_at, view_count, like_count, scraped_at
)
VALUES (
    %(app_id)s, %(video_id)s, %(title)s, %(channel_title)s,
    %(thumbnail_url)s, %(published_at)s, %(view_count)s, %(like_count)s, %(scraped_at)s
)
ON CONFLICT (video_id) DO UPDATE SET
    title         = EXCLUDED.title,
    channel_title = EXCLUDED.channel_title,
    thumbnail_url = EXCLUDED.thumbnail_url,
    published_at  = EXCLUDED.published_at,
    view_count    = EXCLUDED.view_count,
    like_count    = EXCLUDED.like_count,
    scraped_at    = EXCLUDED.scraped_at;
"""


def save_video(cur, record: dict) -> None:
    cur.execute(UPSERT_VIDEO_SQL, record)


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────

def run(
    dry_run: bool = False,
    limit: Optional[int] = None,
    force: bool = False,
) -> None:
    youtube = get_youtube_client()

    if dry_run:
        # In dry-run: load a small sample without hitting DB
        games = [
            {"id": 367520, "name": "Hollow Knight"},
            {"id": 413150, "name": "Stardew Valley"},
            {"id": 1145360, "name": "Hades"},
        ]
        if limit:
            games = games[:limit]
    else:
        games = load_games(limit=limit, force=force)

    logger.info(
        "YouTube ingestor starting — %d games | dry_run=%s | force=%s",
        len(games), dry_run, force,
    )

    # Quota tracker: search costs 100 units, stats costs 1 unit
    quota_used = 0
    DAILY_QUOTA = 9_500   # leave 500 units buffer
    success_count = 0
    skip_count = 0

    for game in games:
        if quota_used >= DAILY_QUOTA:
            logger.warning("Daily quota limit reached (%d units). Stopping.", quota_used)
            break

        game_id   = game["id"]
        game_name = game["name"]
        logger.info("Processing '%s' (app_id=%s)...", game_name, game_id)

        # 1. Search for gameplay video (100 units)
        video_info = search_gameplay_video(youtube, game_name)
        quota_used += 100
        rate_sleep(0.5)

        if not video_info:
            skip_count += 1
            continue

        # 2. Fetch stats (1 unit)
        stats = fetch_video_stats(youtube, video_info["video_id"])
        quota_used += 1
        rate_sleep(0.3)

        record = {
            "app_id":        game_id,
            "video_id":      video_info["video_id"],
            "title":         video_info["title"],
            "channel_title": video_info["channel_title"],
            "thumbnail_url": video_info["thumbnail_url"],
            "published_at":  video_info["published_at"],
            "view_count":    stats["view_count"],
            "like_count":    stats["like_count"],
            "scraped_at":    datetime.now(timezone.utc),
        }

        if dry_run:
            print(json.dumps(
                {**record, "scraped_at": str(record["scraped_at"])},
                indent=2, ensure_ascii=False,
            ))
        else:
            try:
                with db_cursor() as cur:
                    save_video(cur, record)
                logger.info(
                    "  ✓ Saved '%s' — %s (%s views)",
                    game_name, video_info["title"], f"{stats['view_count']:,}"
                )
                success_count += 1
            except Exception as exc:
                logger.error("  ✗ DB error for '%s': %s", game_name, exc)
                skip_count += 1

    logger.info(
        "YouTube ingestor done. Success: %d | Skipped/Failed: %d | Quota used: ~%d units",
        success_count, skip_count, quota_used,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube gameplay video ingestor")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON, skip DB")
    parser.add_argument("--limit", type=int, default=None, help="Max games to process")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch videos even for games that already have one",
    )
    args = parser.parse_args()

    run(dry_run=args.dry_run, limit=args.limit, force=args.force)
