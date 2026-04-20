"""
run_ingest_all.py
=================
Master pipeline: runs all ingestors in the correct dependency order.

Order:
    1. steam_ingestor    -> populates `games` + `steam_reviews`
    2. steamdb_ingestor  -> snapshots SteamDB trending/hot charts
    3. youtube_ingestor  -> reads `games`, populates `youtube_videos`
    4. reddit_ingestor   -> reads `games`, populates `reddit_posts` + `reddit_comments`

Usage:
    python -m jobs.run_ingest_all
    python -m jobs.run_ingest_all --mode indie
    python -m jobs.run_ingest_all --mode hot
    python -m jobs.run_ingest_all --dry-run
    python -m jobs.run_ingest_all --skip-steam
    python -m jobs.run_ingest_all --skip-steamdb
    python -m jobs.run_ingest_all --skip-youtube
    python -m jobs.run_ingest_all --skip-reddit
"""

import argparse
import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("run_ingest_all")


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def run(
    mode: str = "all",
    dry_run: bool = False,
    skip_steam: bool = False,
    skip_steamdb: bool = False,
    skip_youtube: bool = False,
    skip_reddit: bool = False,
    limit: int | None = None,
) -> None:
    pipeline_start = time.time()
    errors: list[str] = []
    free_tier_mode = _env_flag("FREE_TIER_MODE", default=False)

    if free_tier_mode and mode == "all":
        mode = "hot"
    if free_tier_mode and limit is None:
        limit = 25

    if skip_steam:
        logger.info("Skipping Steam ingestor.")
    else:
        logger.info("=" * 60)
        logger.info("STEP 1/4 - Steam ingestor (mode=%s)", mode)
        logger.info("=" * 60)
        try:
            from ingestors.steam_ingestor import run as steam_run
            steam_run(dry_run=dry_run, limit=limit, mode=mode)
        except Exception as exc:
            logger.error("Steam ingestor failed: %s", exc)
            errors.append(f"Steam: {exc}")

    if skip_steamdb:
        logger.info("Skipping SteamDB ingestor.")
    else:
        logger.info("=" * 60)
        logger.info("STEP 2/4 - SteamDB ingestor")
        logger.info("=" * 60)
        try:
            from ingestors.steamdb_ingestor import run as steamdb_run
            steamdb_run(dry_run=dry_run, limit=limit)
        except Exception as exc:
            logger.error("SteamDB ingestor failed: %s", exc)
            errors.append(f"SteamDB: {exc}")

    if skip_youtube:
        logger.info("Skipping YouTube ingestor.")
    else:
        logger.info("=" * 60)
        logger.info("STEP 3/4 - YouTube ingestor")
        logger.info("=" * 60)
        try:
            from ingestors.youtube_ingestor import run as youtube_run
            youtube_run(dry_run=dry_run, limit=limit)
        except Exception as exc:
            logger.error("YouTube ingestor failed: %s", exc)
            errors.append(f"YouTube: {exc}")

    if skip_reddit:
        logger.info("Skipping Reddit ingestor.")
    else:
        logger.info("=" * 60)
        logger.info("STEP 4/4 - Reddit ingestor")
        logger.info("=" * 60)
        try:
            from ingestors.reddit_ingestor import run as reddit_run
            reddit_run(dry_run=dry_run, limit=limit)
        except Exception as exc:
            logger.error("Reddit ingestor failed: %s", exc)
            errors.append(f"Reddit: {exc}")

    elapsed = time.time() - pipeline_start
    mins, secs = divmod(int(elapsed), 60)
    logger.info("=" * 60)
    if errors:
        logger.warning("Pipeline finished with %d error(s) in %dm %ds:", len(errors), mins, secs)
        for err in errors:
            logger.warning("  - %s", err)
        sys.exit(1)
    else:
        logger.info("Pipeline complete in %dm %ds - all steps succeeded.", mins, secs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run full data ingestion pipeline")
    parser.add_argument("--mode", choices=["indie", "hot", "all"], default="all", help="Steam game selection mode")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON, skip DB writes")
    parser.add_argument("--skip-steam", action="store_true", help="Skip Steam ingestor")
    parser.add_argument("--skip-steamdb", action="store_true", help="Skip SteamDB ingestor")
    parser.add_argument("--skip-youtube", action="store_true", help="Skip YouTube ingestor")
    parser.add_argument("--skip-reddit", action="store_true", help="Skip Reddit ingestor")
    parser.add_argument("--limit", type=int, default=None, help="Max games per ingestor")
    args = parser.parse_args()

    run(
        mode=args.mode,
        dry_run=args.dry_run,
        skip_steam=args.skip_steam,
        skip_steamdb=args.skip_steamdb,
        skip_youtube=args.skip_youtube,
        skip_reddit=args.skip_reddit,
        limit=args.limit,
    )
