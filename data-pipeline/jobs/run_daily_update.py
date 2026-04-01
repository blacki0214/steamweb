"""
run_daily_update.py
===================
Daily refresh pipeline for cloud execution.

Default behavior:
    1) verify DB connection target and readiness
    2) refresh Steam games/reviews
    3) snapshot SteamDB charts
    4) refresh YouTube and Reddit for new games

Environment toggles:
    DAILY_INCLUDE_STEAM=true|false   (default: true)
    DAILY_STEAM_MODE=indie|hot|all   (default: all)

Usage:
    python -m jobs.run_daily_update
"""

import logging
import os
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("run_daily_update")


def run() -> None:
    start = time.time()
    errors: list[str] = []
    include_steam = os.getenv("DAILY_INCLUDE_STEAM", "true").strip().lower() not in {"0", "false", "no"}
    steam_mode = os.getenv("DAILY_STEAM_MODE", "all").strip().lower()
    if steam_mode not in {"indie", "hot", "all"}:
        steam_mode = "all"

    logger.info("🔌 Daily update — checking database readiness...")
    try:
        from ingestors.utils import assert_database_ready
        assert_database_ready()
    except Exception as exc:
        logger.error("Database check failed: %s", exc)
        raise

    if include_steam:
        logger.info("🎮 Daily update — Steam games/reviews (mode=%s)...", steam_mode)
        try:
            from ingestors.steam_ingestor import run as steam_run
            steam_run(dry_run=False, mode=steam_mode)
        except Exception as exc:
            logger.error("Steam update failed: %s", exc)
            errors.append(str(exc))
    else:
        logger.info("⏭️ Daily update — Steam step disabled by DAILY_INCLUDE_STEAM=false")

    # Daily: snapshot SteamDB trending/hot charts
    logger.info("📈 Daily update — SteamDB charts...")
    try:
        from ingestors.steamdb_ingestor import run as steamdb_run
        steamdb_run(dry_run=False)
    except Exception as exc:
        logger.error("SteamDB update failed: %s", exc)
        errors.append(str(exc))

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
        # Cloud job should still succeed on partial-source issues (e.g., Reddit rate limits/blocks).
        # We keep full visibility through warning logs and error count.
        logger.warning(
            "Daily update finished with non-fatal errors in %dm %ds (count=%d).",
            mins,
            secs,
            len(errors),
        )
        logger.warning("Error summary: %s", " | ".join(errors[:5]))
    else:
        logger.info("✅ Daily update complete in %dm %ds.", mins, secs)


if __name__ == "__main__":
    run()
