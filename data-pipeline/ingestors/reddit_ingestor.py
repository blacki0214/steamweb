"""
Reddit Ingestor
===============
Fetches game-related posts and comments from Reddit.

Supports two modes:
    1) OAuth API (recommended for cloud): uses app credentials
    2) Public JSON API fallback (unauthenticated)

Endpoints used:
    - OAuth token      : https://www.reddit.com/api/v1/access_token
    - Sitewide search  : /search
    - Post comments    : /r/{sub}/comments/{id}

Env vars:
    - REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
    - optional: REDDIT_USERNAME, REDDIT_PASSWORD (script/password grant)
    - REDDIT_USER_AGENT (required by Reddit API policy)

We use a 1.5s delay between requests to stay safe.

Run:
    python -m ingestors.reddit_ingestor              # all games in DB
    python -m ingestors.reddit_ingestor --dry-run    # print JSON, no DB write
    python -m ingestors.reddit_ingestor --limit 5    # only 5 games
    python -m ingestors.reddit_ingestor --force      # re-fetch existing games
"""

import argparse
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
import re

import requests
from dotenv import load_dotenv

from ingestors.utils import db_cursor, rate_sleep

load_dotenv()
logger = logging.getLogger(__name__)

USER_AGENT    = os.getenv("REDDIT_USER_AGENT", "IndieGameBot/1.0")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "").strip()
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME", "").strip()
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD", "").strip()

OAUTH_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
OAUTH_API_BASE = "https://oauth.reddit.com"
PUBLIC_API_BASE = "https://www.reddit.com"

SUBREDDIT_FILTERS = [
    s.strip()
    for s in os.getenv("REDDIT_SUBREDDITS", "").split(",")
    if s.strip()
]
POSTS_PER_GAME = 10   # posts to fetch per game from sitewide search
COMMENTS_PER_POST = 10  # top comments per post

_oauth_token: str | None = None
_oauth_expires_at: datetime | None = None


# ──────────────────────────────────────────────
# Fetch helpers
# ──────────────────────────────────────────────

def oauth_enabled() -> bool:
    return bool(REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET)


def _token_is_valid() -> bool:
    if not _oauth_token or not _oauth_expires_at:
        return False
    return datetime.now(timezone.utc) < _oauth_expires_at


def get_oauth_token() -> str:
    """Get or refresh OAuth token for Reddit API."""
    global _oauth_token, _oauth_expires_at

    if _token_is_valid() and _oauth_token:
        return _oauth_token

    if not oauth_enabled():
        raise RuntimeError("Reddit OAuth is not configured")

    grant_data: dict[str, str] = {"grant_type": "client_credentials"}
    if REDDIT_USERNAME and REDDIT_PASSWORD:
        grant_data = {
            "grant_type": "password",
            "username": REDDIT_USERNAME,
            "password": REDDIT_PASSWORD,
        }

    resp = requests.post(
        OAUTH_TOKEN_URL,
        data=grant_data,
        auth=(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET),
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    resp.raise_for_status()
    payload = resp.json()

    access_token = payload.get("access_token")
    expires_in = int(payload.get("expires_in", 3600))
    if not access_token:
        raise RuntimeError("OAuth token response missing access_token")

    _oauth_token = str(access_token)
    _oauth_expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(30, expires_in - 60))
    return _oauth_token


def reddit_get(path: str, params: dict) -> requests.Response:
    """GET helper that prefers OAuth endpoint and falls back to public API."""
    base_params = {**params, "raw_json": 1}
    if oauth_enabled():
        token = get_oauth_token()
        headers = {
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {token}",
        }
        return requests.get(
            f"{OAUTH_API_BASE}{path}.json",
            params=base_params,
            headers=headers,
            timeout=20,
        )

    return requests.get(
        f"{PUBLIC_API_BASE}{path}.json",
        params=base_params,
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )

def _is_relevant_post(game_name: str, post: dict) -> bool:
    """Keep only posts that likely refer to the game name."""
    haystack = f"{post.get('title', '')} {post.get('selftext', '')}".lower()
    game_l = game_name.lower()
    if game_l in haystack:
        return True

    tokens = [t for t in re.split(r"\W+", game_l) if len(t) >= 4]
    return any(token in haystack for token in tokens)


def search_posts(game_name: str, limit: int = POSTS_PER_GAME) -> list[dict]:
    """Search Reddit sitewide for posts about a game and apply lightweight filtering."""
    try:
        resp = reddit_get(
            "/search",
            {
                "q": game_name,
                "sort": "top",
                "t": "year",       # posts from the last year
                "limit": limit,
                "type": "link",
            },
        )
        resp.raise_for_status()
        children = resp.json().get("data", {}).get("children", [])
        posts = [c["data"] for c in children if c.get("kind") == "t3"]

        if SUBREDDIT_FILTERS:
            allowed = {s.lower() for s in SUBREDDIT_FILTERS}
            posts = [p for p in posts if str(p.get("subreddit", "")).lower() in allowed]

        return [p for p in posts if _is_relevant_post(game_name, p)]
    except Exception as exc:
        logger.warning("Reddit search failed ['%s']: %s", game_name, exc)
        return []


def fetch_comments(subreddit: str, post_id: str, limit: int = COMMENTS_PER_POST) -> list[dict]:
    """Fetch top-level comments for a given post. Returns list of comment dicts."""
    try:
        resp = reddit_get(
            f"/r/{subreddit}/comments/{post_id}",
            {"limit": limit, "sort": "top", "depth": 1},
        )
        resp.raise_for_status()
        data = resp.json()
        # Response is [post_listing, comment_listing]
        if not isinstance(data, list) or len(data) < 2:
            return []
        comment_children = data[1].get("data", {}).get("children", [])
        return [
            c["data"] for c in comment_children
            if c.get("kind") == "t1" and c["data"].get("body", "") not in ("[deleted]", "[removed]", "")
        ]
    except Exception as exc:
        logger.warning("Reddit comments failed [post=%s]: %s", post_id, exc)
        return []


# ──────────────────────────────────────────────
# Transform helpers
# ──────────────────────────────────────────────

def parse_post(raw: dict, app_id: int) -> dict:
    return {
        "id":           raw["id"],
        "app_id":       app_id,
        "subreddit":    raw.get("subreddit", ""),
        "title":        raw.get("title", ""),
        "selftext":     raw.get("selftext", "")[:2000],  # cap at 2000 chars
        "score":        raw.get("score", 0),
        "upvote_ratio": raw.get("upvote_ratio"),
        "num_comments": raw.get("num_comments", 0),
        "url":          raw.get("url", ""),
        "created_utc":  datetime.fromtimestamp(
            raw.get("created_utc", 0), tz=timezone.utc
        ),
        "scraped_at":   datetime.now(timezone.utc),
    }


def parse_comment(raw: dict, post_id: str, app_id: int) -> dict:
    return {
        "id":          raw["id"],
        "post_id":     post_id,
        "app_id":      app_id,
        "body":        raw.get("body", "")[:1000],  # cap at 1000 chars
        "score":       raw.get("score", 0),
        "created_utc": datetime.fromtimestamp(
            raw.get("created_utc", 0), tz=timezone.utc
        ),
        "scraped_at":  datetime.now(timezone.utc),
    }


# ──────────────────────────────────────────────
# DB helpers
# ──────────────────────────────────────────────

def load_games(limit: Optional[int] = None, force: bool = False) -> list[dict]:
    """Load games that need Reddit data."""
    if force:
        sql = "SELECT id, name FROM games ORDER BY id LIMIT %(limit)s"
    else:
        sql = """
            SELECT g.id, g.name
            FROM games g
            LEFT JOIN reddit_posts rp ON rp.app_id = g.id
            WHERE rp.id IS NULL
            ORDER BY g.id
            LIMIT %(limit)s
        """
    with db_cursor() as cur:
        cur.execute(sql, {"limit": limit or 10_000})
        return [dict(row) for row in cur.fetchall()]


UPSERT_POST_SQL = """
INSERT INTO reddit_posts (
    id, app_id, subreddit, title, selftext,
    score, upvote_ratio, num_comments, url, created_utc, scraped_at
)
VALUES (
    %(id)s, %(app_id)s, %(subreddit)s, %(title)s, %(selftext)s,
    %(score)s, %(upvote_ratio)s, %(num_comments)s, %(url)s, %(created_utc)s, %(scraped_at)s
)
ON CONFLICT (id) DO UPDATE SET
    score        = EXCLUDED.score,
    num_comments = EXCLUDED.num_comments,
    scraped_at   = EXCLUDED.scraped_at;
"""

UPSERT_COMMENT_SQL = """
INSERT INTO reddit_comments (id, post_id, app_id, body, score, created_utc, scraped_at)
VALUES (%(id)s, %(post_id)s, %(app_id)s, %(body)s, %(score)s, %(created_utc)s, %(scraped_at)s)
ON CONFLICT (id) DO UPDATE SET
    score      = EXCLUDED.score,
    scraped_at = EXCLUDED.scraped_at;
"""


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────

def run(
    dry_run: bool = False,
    limit: Optional[int] = None,
    force: bool = False,
) -> None:

    if oauth_enabled():
        logger.info("Reddit OAuth enabled (authenticated API mode)")
    else:
        logger.warning("Reddit OAuth not configured; using unauthenticated public API mode")

    if dry_run:
        games = [
            {"id": 367520,  "name": "Hollow Knight"},
            {"id": 413150,  "name": "Stardew Valley"},
            {"id": 1145360, "name": "Hades"},
        ]
        if limit:
            games = games[:limit]
    else:
        games = load_games(limit=limit, force=force)

    logger.info(
        "Reddit ingestor starting — %d games | dry_run=%s | force=%s",
        len(games), dry_run, force,
    )

    total_posts_fetched    = 0
    total_comments_fetched = 0
    total_posts_saved      = 0
    total_comments_saved   = 0

    for game in games:
        app_id    = game["id"]
        game_name = game["name"]
        logger.info("Processing '%s' (app_id=%s)...", game_name, app_id)

        all_posts: list[dict] = []
        all_comments: list[dict] = []

        raw_posts = search_posts(game_name)
        rate_sleep(1.5)

        for raw_post in raw_posts:
            post = parse_post(raw_post, app_id)
            all_posts.append(post)

            # Fetch comments from the originating subreddit of the post.
            subreddit = str(raw_post.get("subreddit", ""))
            if not subreddit:
                continue

            raw_comments = fetch_comments(subreddit, raw_post["id"])
            rate_sleep(1.5)

            for raw_comment in raw_comments:
                comment = parse_comment(raw_comment, raw_post["id"], app_id)
                all_comments.append(comment)

        total_posts_fetched    += len(all_posts)
        total_comments_fetched += len(all_comments)

        if dry_run:
            print(json.dumps(
                {
                    "game": game_name,
                    "posts_found": len(all_posts),
                    "comments_found": len(all_comments),
                    "sample_post": {
                        **all_posts[0],
                        "created_utc": str(all_posts[0]["created_utc"]),
                        "scraped_at": str(all_posts[0]["scraped_at"]),
                    } if all_posts else None,
                },
                indent=2, ensure_ascii=False,
            ))
        else:
            try:
                with db_cursor() as cur:
                    for post in all_posts:
                        cur.execute(UPSERT_POST_SQL, post)
                    for comment in all_comments:
                        cur.execute(UPSERT_COMMENT_SQL, comment)
                total_posts_saved    += len(all_posts)
                total_comments_saved += len(all_comments)
                logger.info(
                    "  ✓ Saved %d posts, %d comments for '%s'",
                    len(all_posts), len(all_comments), game_name,
                )
            except Exception as exc:
                logger.error("  ✗ DB error for '%s': %s", game_name, exc)

    if dry_run:
        logger.info(
            "Reddit ingestor done (DRY RUN). Fetched %d posts, %d comments — nothing saved to DB.",
            total_posts_fetched, total_comments_fetched,
        )
    else:
        logger.info(
            "Reddit ingestor done. Saved: %d posts | %d comments",
            total_posts_saved, total_comments_saved,
        )




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reddit game discussion ingestor")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON, skip DB")
    parser.add_argument("--limit", type=int, default=None, help="Max games to process")
    parser.add_argument("--force", action="store_true", help="Re-fetch existing games")
    args = parser.parse_args()

    run(dry_run=args.dry_run, limit=args.limit, force=args.force)
