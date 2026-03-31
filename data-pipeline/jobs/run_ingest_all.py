"""
run_ingest_all.py
=================
Master pipeline: runs all 3 ingestors in the correct dependency order.

Order:
  1. steam_ingestor   → populates `games` + `steam_reviews`
  2. youtube_ingestor → reads `games`, populates `youtube_videos`
  3. reddit_ingestor  → reads `games`, populates `reddit_posts` + `reddit_comments`

Usage:
    python -m jobs.run_ingest_all                  # full pipeline (indie + hot)
    python -m jobs.run_ingest_all --mode indie      # indie games only
    python -m jobs.run_ingest_all --mode hot        # hot games only
    python -m jobs.run_ingest_all --dry-run         # test all 3 without writing DB
    python -m jobs.run_ingest_all --skip-steam      # skip Steam (games already in DB)
    python -m jobs.run_ingest_all --skip-youtube    # skip YouTube step
    python -m jobs.run_ingest_all --skip-reddit     # skip Reddit step
"""

import argparse
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("run_ingest_all")


def run(
    mode: str = "all",
    dry_run: bool = False,
    skip_steam: bool = False,
    skip_youtube: bool = False,
    skip_reddit: bool = False,
    limit: int | None = None,
) -> None:

    pipeline_start = time.time()
    errors: list[str] = []

    # ── Step 1: Steam ──────────────────────────────────────────
    if skip_steam:
        logger.info("⏭️  Skipping Steam ingestor.")
    else:
        logger.info("=" * 60)
        logger.info("🎮 STEP 1/3 — Steam ingestor (mode=%s)", mode)
        logger.info("=" * 60)
        try:
            from ingestors.steam_ingestor import run as steam_run
            steam_run(dry_run=dry_run, limit=limit, mode=mode)
        except Exception as exc:
            logger.error("Steam ingestor FAILED: %s", exc)
            errors.append(f"Steam: {exc}")

    # ── Step 2: YouTube ────────────────────────────────────────
    if skip_youtube:
        logger.info("⏭️  Skipping YouTube ingestor.")
    else:
        logger.info("=" * 60)
        logger.info("📺 STEP 2/3 — YouTube ingestor")
        logger.info("=" * 60)
        try:
            from ingestors.youtube_ingestor import run as youtube_run
            youtube_run(dry_run=dry_run, limit=limit)
        except Exception as exc:
            logger.error("YouTube ingestor FAILED: %s", exc)
            errors.append(f"YouTube: {exc}")

    # ── Step 3: Reddit ─────────────────────────────────────────
    if skip_reddit:
        logger.info("⏭️  Skipping Reddit ingestor.")
    else:
        logger.info("=" * 60)
        logger.info("🤖 STEP 3/3 — Reddit ingestor")
        logger.info("=" * 60)
        try:
            from ingestors.reddit_ingestor import run as reddit_run
            reddit_run(dry_run=dry_run, limit=limit)
        except Exception as exc:
            logger.error("Reddit ingestor FAILED: %s", exc)
            errors.append(f"Reddit: {exc}")

    # ── Summary ────────────────────────────────────────────────
    elapsed = time.time() - pipeline_start
    mins, secs = divmod(int(elapsed), 60)
    logger.info("=" * 60)
    if errors:
        logger.warning("Pipeline finished with %d error(s) in %dm %ds:", len(errors), mins, secs)
        for err in errors:
            logger.warning("  ✗ %s", err)
        sys.exit(1)
    else:
        logger.info("✅ Pipeline complete in %dm %ds — all steps succeeded.", mins, secs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run full data ingestion pipeline")
    parser.add_argument(
        "--mode", choices=["indie", "hot", "all"], default="all",
        help="Steam game selection mode (default: all)",
    )
    parser.add_argument("--dry-run",      action="store_true", help="Print JSON, skip DB writes")
    parser.add_argument("--skip-steam",   action="store_true", help="Skip Steam ingestor")
    parser.add_argument("--skip-youtube", action="store_true", help="Skip YouTube ingestor")
    parser.add_argument("--skip-reddit",  action="store_true", help="Skip Reddit ingestor")
    parser.add_argument("--limit", type=int, default=None, help="Max games per ingestor")
    args = parser.parse_args()

    run(
        mode=args.mode,
        dry_run=args.dry_run,
        skip_steam=args.skip_steam,
        skip_youtube=args.skip_youtube,
        skip_reddit=args.skip_reddit,
        limit=args.limit,
    )
