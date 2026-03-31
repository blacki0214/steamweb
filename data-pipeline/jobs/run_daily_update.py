"""
run_daily_update.py
===================
Lightweight daily refresh: skips Steam (games already seeded),
only updates YouTube stats and Reddit discussions for existing games.

Usage:
    python -m jobs.run_daily_update
"""

import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("run_daily_update")


def run() -> None:
    start = time.time()
    errors: list[str] = []

    # Daily: only fetch YouTube videos for new games (skip existing)
    logger.info("📺 Daily update — YouTube (new games only)...")
    try:
        from ingestors.youtube_ingestor import run as youtube_run
        youtube_run(dry_run=False, force=False)
    except Exception as exc:
        logger.error("YouTube update failed: %s", exc)
        errors.append(str(exc))

    # Daily: only fetch Reddit posts for new games (skip existing)
    logger.info("🤖 Daily update — Reddit (new games only)...")
    try:
        from ingestors.reddit_ingestor import run as reddit_run
        reddit_run(dry_run=False, force=False)
    except Exception as exc:
        logger.error("Reddit update failed: %s", exc)
        errors.append(str(exc))

    elapsed = time.time() - start
    mins, secs = divmod(int(elapsed), 60)
    if errors:
        logger.warning("Daily update finished with errors in %dm %ds.", mins, secs)
        sys.exit(1)
    else:
        logger.info("✅ Daily update complete in %dm %ds.", mins, secs)


if __name__ == "__main__":
    run()
