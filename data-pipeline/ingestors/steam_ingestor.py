"""
Steam Ingestor
==============
Fetches game metadata and reviews from the Steam public API.

Endpoints used (no API key required for public endpoints):
  - appdetails    : https://store.steampowered.com/api/appdetails?appids={id}
  - appreviews    : https://store.steampowered.com/appreviews/{id}?json=1
  - most played   : https://api.steampowered.com/ISteamChartsAPI/GetMostPlayedGames/v1/
  - top sellers   : https://store.steampowered.com/api/featuredcategories

Run:
    python -m ingestors.steam_ingestor                       # indie + hot (all)
    python -m ingestors.steam_ingestor --mode indie          # only seed indie list
    python -m ingestors.steam_ingestor --mode hot            # only live hot games
    python -m ingestors.steam_ingestor --mode all            # indie + hot, deduplicated
    python -m ingestors.steam_ingestor --dry-run --limit 5   # print JSON, no DB write
"""

import argparse
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

import requests
from dotenv import load_dotenv

from ingestors.utils import db_cursor, rate_sleep

load_dotenv()
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────

APPDETAILS_URL    = "https://store.steampowered.com/api/appdetails"
APPREVIEWS_URL    = "https://store.steampowered.com/appreviews/{app_id}"
MOST_PLAYED_URL   = "https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/"
FEATURED_CAT_URL  = "https://store.steampowered.com/api/featuredcategories"
STORE_SEARCH_URL  = "https://store.steampowered.com/search/results"
REVIEWS_PER_GAME  = 20
HOT_GAMES_LIMIT   = 50   # how many top-played games to pull
INDIE_TAG_ID      = 492  # Steam tag ID for "Indie"
INDIE_LIMIT       = 50   # how many indie games to fetch dynamically


# ──────────────────────────────────────────────
# Indie-game ID fetcher  (dynamic, no hardcoding)
# ──────────────────────────────────────────────

def fetch_indie_app_ids(limit: int = INDIE_LIMIT) -> list[int]:
    """
    Fetch top-rated indie game app_ids from Steam Store Search.
    Uses tag 492 (Indie), sorted by review count — always up-to-date.

    Note: Steam returns IDs as "app_XXXXXX" strings — we strip the prefix.
    """
    ids: list[int] = []
    page = 1
    max_pages = 10  # safeguard: never exceed 10 pages (~250 games max)

    while len(ids) < limit and page <= max_pages:
        try:
            resp = requests.get(
                STORE_SEARCH_URL,
                params={
                    "tags": INDIE_TAG_ID,
                    "sort_by": "Reviews",  # sort by total reviews (most popular)
                    "category1": 998,      # games only (exclude DLC/software)
                    "json": 1,
                    "page": page,
                    "cc": "us",
                    "l": "english",
                },
                timeout=15,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items:
                break

            for item in items:
                raw_id = item.get("id") or item.get("appid")
                if not raw_id:
                    # Fallback: extract app_id from logo URL
                    # e.g. https://.../steam/apps/367520/capsule.jpg
                    logo = item.get("logo", "")
                    match = re.search(r"/apps/(\d+)/", logo)
                    if match:
                        raw_id = match.group(1)
                    else:
                        continue
                # Steam sometimes returns IDs as "app_367520" strings
                if isinstance(raw_id, str) and raw_id.startswith("app_"):
                    raw_id = raw_id[4:]
                try:
                    ids.append(int(raw_id))
                except (ValueError, TypeError):
                    continue

            logger.info("  page=%d → collected %d ids so far", page, len(ids))
            page += 1
            rate_sleep(1.0)

        except Exception as exc:
            logger.error("fetch_indie_app_ids page=%d failed: %s", page, exc)
            break

    ids = ids[:limit]
    logger.info("Indie (dynamic): fetched %d app_ids from Steam Store Search", len(ids))
    return ids


# ──────────────────────────────────────────────
# Hot-game ID fetchers  (dynamic, no key needed)
# ──────────────────────────────────────────────

def fetch_most_played_ids(limit: int = HOT_GAMES_LIMIT) -> list[int]:
    """Return top-N app_ids by current concurrent players (Steam Charts)."""
    try:
        resp = requests.get(MOST_PLAYED_URL, timeout=15)
        resp.raise_for_status()
        ranks = resp.json().get("response", {}).get("ranks", [])
        ids = [int(r["appid"]) for r in ranks[:limit] if "appid" in r]
        logger.info("Most-played: fetched %d app_ids", len(ids))
        return ids
    except Exception as exc:
        logger.error("fetch_most_played_ids failed: %s", exc)
        return []


def fetch_top_seller_ids(limit: int = HOT_GAMES_LIMIT) -> list[int]:
    """Return top-seller app_ids from Steam featured categories."""
    try:
        resp = requests.get(
            FEATURED_CAT_URL,
            params={"cc": "us", "l": "english"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("top_sellers", {}).get("items", [])
        ids = [int(i["id"]) for i in items[:limit] if "id" in i]
        logger.info("Top-sellers: fetched %d app_ids", len(ids))
        return ids
    except Exception as exc:
        logger.error("fetch_top_seller_ids failed: %s", exc)
        return []


def build_app_id_list(mode: str = "all") -> list[int]:
    """
    mode='indie' → top-rated indie games fetched live from Steam Store Search
    mode='hot'   → most played + top sellers (live from Steam Charts)
    mode='all'   → indie + hot, deduplicated, indie games first
    All sources are 100% dynamic — no hardcoded lists.
    """
    if mode == "indie":
        return fetch_indie_app_ids()

    hot_ids = fetch_most_played_ids() + fetch_top_seller_ids()
    # deduplicate while preserving order
    seen: set[int] = set()
    unique_hot: list[int] = []
    for aid in hot_ids:
        if aid not in seen:
            seen.add(aid)
            unique_hot.append(aid)

    if mode == "hot":
        return unique_hot

    # mode == "all": indie first, then hot games not already in indie list
    indie_ids = fetch_indie_app_ids()
    indie_set = set(indie_ids)
    all_ids = indie_ids[:]
    for aid in unique_hot:
        if aid not in indie_set:
            all_ids.append(aid)
    return all_ids


# ──────────────────────────────────────────────
# Fetch helpers
# ──────────────────────────────────────────────

def fetch_app_details(app_id: int) -> Optional[dict]:
    """Call Steam appdetails endpoint and return the parsed data dict."""
    try:
        resp = requests.get(
            APPDETAILS_URL,
            params={"appids": app_id, "cc": "us", "l": "english"},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        entry = payload.get(str(app_id), {})
        if not entry.get("success"):
            logger.warning("appdetails: app_id %s returned success=false", app_id)
            return None
        return entry["data"]
    except Exception as exc:
        logger.error("appdetails failed for %s: %s", app_id, exc)
        return None


def fetch_app_reviews(app_id: int, num: int = REVIEWS_PER_GAME) -> list[dict]:
    """Call Steam appreviews endpoint and return a list of review dicts."""
    try:
        resp = requests.get(
            APPREVIEWS_URL.format(app_id=app_id),
            params={
                "json": 1,
                "filter": "recent",
                "language": "english",
                "num_per_page": num,
                "purchase_type": "all",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("success") != 1:
            logger.warning("appreviews: app_id %s returned success != 1", app_id)
            return []
        return data.get("reviews", [])
    except Exception as exc:
        logger.error("appreviews failed for %s: %s", app_id, exc)
        return []


# ──────────────────────────────────────────────
# Transform helpers
# ──────────────────────────────────────────────

def parse_game(app_id: int, data: dict) -> dict:
    """Map raw Steam appdetails data → clean game dict."""
    genres = [g["description"] for g in data.get("genres", [])]
    tags = [c["description"] for c in data.get("categories", [])]

    price_info = data.get("price_overview", {})
    price_usd = None
    if price_info:
        price_usd = round(price_info.get("final", 0) / 100, 2)

    metacritic = data.get("metacritic", {})

    return {
        "id": app_id,
        "name": data.get("name", ""),
        "description": data.get("detailed_description", ""),
        "short_description": data.get("short_description", ""),
        "header_image": data.get("header_image", ""),
        "genres": genres,
        "tags": tags,
        "price_usd": price_usd,
        "is_free": data.get("is_free", False),
        "metacritic_score": metacritic.get("score"),
        "release_date": data.get("release_date", {}).get("date", ""),
        "developer": ", ".join(data.get("developers", [])),
        "publisher": ", ".join(data.get("publishers", [])),
        "website": data.get("website", ""),
        "total_reviews": data.get("recommendations", {}).get("total", 0),
        "scraped_at": datetime.now(timezone.utc),
    }


def parse_reviews(app_id: int, raw_reviews: list[dict]) -> list[dict]:
    """Map raw Steam review list → clean review dicts."""
    out = []
    for r in raw_reviews:
        out.append({
            "app_id": app_id,
            "recommendation_id": str(r.get("recommendationid", "")),
            "author_steamid": r.get("author", {}).get("steamid", ""),
            "voted_up": r.get("voted_up", False),
            "playtime_hours": round(
                r.get("author", {}).get("playtime_at_review", 0) / 60, 1
            ),
            "review_text": r.get("review", ""),
            "votes_helpful": r.get("votes_helpful", 0),
            "created_at": datetime.fromtimestamp(
                r.get("timestamp_created", 0), tz=timezone.utc
            ),
            "scraped_at": datetime.now(timezone.utc),
        })
    return out


# ──────────────────────────────────────────────
# DB upsert helpers
# ──────────────────────────────────────────────

UPSERT_GAME_SQL = """
INSERT INTO games (
    id, name, description, short_description, header_image,
    genres, tags, price_usd, is_free, metacritic_score,
    release_date, developer, publisher, website,
    total_reviews, scraped_at
)
VALUES (
    %(id)s, %(name)s, %(description)s, %(short_description)s, %(header_image)s,
    %(genres)s, %(tags)s, %(price_usd)s, %(is_free)s, %(metacritic_score)s,
    %(release_date)s, %(developer)s, %(publisher)s, %(website)s,
    %(total_reviews)s, %(scraped_at)s
)
ON CONFLICT (id) DO UPDATE SET
    name              = EXCLUDED.name,
    description       = EXCLUDED.description,
    short_description = EXCLUDED.short_description,
    header_image      = EXCLUDED.header_image,
    genres            = EXCLUDED.genres,
    tags              = EXCLUDED.tags,
    price_usd         = EXCLUDED.price_usd,
    is_free           = EXCLUDED.is_free,
    metacritic_score  = EXCLUDED.metacritic_score,
    release_date      = EXCLUDED.release_date,
    developer         = EXCLUDED.developer,
    publisher         = EXCLUDED.publisher,
    website           = EXCLUDED.website,
    total_reviews     = EXCLUDED.total_reviews,
    scraped_at        = EXCLUDED.scraped_at;
"""

UPSERT_REVIEW_SQL = """
INSERT INTO steam_reviews (
    app_id, recommendation_id, author_steamid,
    voted_up, playtime_hours, review_text,
    votes_helpful, created_at, scraped_at
)
VALUES (
    %(app_id)s, %(recommendation_id)s, %(author_steamid)s,
    %(voted_up)s, %(playtime_hours)s, %(review_text)s,
    %(votes_helpful)s, %(created_at)s, %(scraped_at)s
)
ON CONFLICT (recommendation_id) DO NOTHING;
"""


def save_game(cur, game: dict) -> None:
    cur.execute(UPSERT_GAME_SQL, game)


def save_reviews(cur, reviews: list[dict]) -> None:
    for review in reviews:
        cur.execute(UPSERT_REVIEW_SQL, review)


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────

def run(dry_run: bool = False, limit: Optional[int] = None, mode: str = "all") -> None:
    app_ids = build_app_id_list(mode)
    if limit:
        app_ids = app_ids[:limit]
    logger.info(
        "Steam ingestor starting — mode=%s | %d games | dry_run=%s",
        mode, len(app_ids), dry_run
    )

    success_count = 0
    fail_count = 0

    for app_id in app_ids:
        logger.info("Processing app_id=%s ...", app_id)

        # 1. Fetch metadata
        details = fetch_app_details(app_id)
        rate_sleep(1.5)

        if not details:
            fail_count += 1
            continue

        game = parse_game(app_id, details)

        # 2. Fetch reviews
        raw_reviews = fetch_app_reviews(app_id)
        rate_sleep(1.5)
        reviews = parse_reviews(app_id, raw_reviews)

        if dry_run:
            print(json.dumps(
                {**game, "scraped_at": str(game["scraped_at"]), "reviews": [
                    {**r, "created_at": str(r["created_at"]), "scraped_at": str(r["scraped_at"])}
                    for r in reviews
                ]},
                indent=2, ensure_ascii=False
            ))
        else:
            try:
                with db_cursor() as cur:
                    save_game(cur, game)
                    save_reviews(cur, reviews)
                logger.info(
                    "  ✓ Saved '%s' with %d reviews", game["name"], len(reviews)
                )
                success_count += 1
            except Exception as exc:
                logger.error("  ✗ DB error for app_id=%s: %s", app_id, exc)
                fail_count += 1

    logger.info(
        "Steam ingestor done. Success: %d | Failed: %d", success_count, fail_count
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Steam game data ingestor")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON, skip DB")
    parser.add_argument("--limit", type=int, default=None, help="Max number of games to process")
    parser.add_argument(
        "--mode",
        choices=["indie", "hot", "all"],
        default="all",
        help="indie=seed list only | hot=live Steam charts | all=both (default)",
    )
    args = parser.parse_args()

    run(dry_run=args.dry_run, limit=args.limit, mode=args.mode)
