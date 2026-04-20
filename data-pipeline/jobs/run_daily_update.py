"""
run_daily_update.py
===================
Daily refresh pipeline for cloud execution.

Default behavior:
    1) verify DB connection target and readiness
    2) refresh Steam games/reviews
    3) snapshot SteamDB charts
    4) refresh YouTube and Reddit for new games
    5) optionally apply retention cleanup

Environment toggles:
    DAILY_INCLUDE_STEAM=true|false   (default: true)
    DAILY_STEAM_MODE=indie|hot|all   (default: all)
    FREE_TIER_MODE=true|false        (default: false)
    DAILY_RUN_RETENTION=true|false   (default: true in FREE_TIER_MODE)

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


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def run() -> None:
    start = time.time()
    errors: list[str] = []
    free_tier_mode = _env_flag("FREE_TIER_MODE", default=False)
    include_steam = _env_flag("DAILY_INCLUDE_STEAM", default=True)
    steam_mode = os.getenv("DAILY_STEAM_MODE", "all").strip().lower()
    if steam_mode not in {"indie", "hot", "all"}:
        steam_mode = "all"
    if free_tier_mode and steam_mode == "all":
        steam_mode = "hot"

    run_retention = _env_flag("DAILY_RUN_RETENTION", default=free_tier_mode)

    logger.info("Daily update: checking database readiness...")
    try:
        from ingestors.utils import assert_database_ready
        assert_database_ready()
    except Exception as exc:
        logger.error("Database check failed: %s", exc)
        raise

    if include_steam:
        logger.info("Daily update: Steam games/reviews (mode=%s)...", steam_mode)
        try:
            from ingestors.steam_ingestor import run as steam_run
            steam_limit = 25 if free_tier_mode else None
            steam_run(dry_run=False, mode=steam_mode, limit=steam_limit)
        except Exception as exc:
            logger.error("Steam update failed: %s", exc)
            errors.append(str(exc))
    else:
        logger.info("Daily update: Steam step disabled by DAILY_INCLUDE_STEAM=false")

    logger.info("Daily update: SteamDB charts...")
    try:
        from ingestors.steamdb_ingestor import run as steamdb_run
        steamdb_limit = 25 if free_tier_mode else None
        steamdb_run(dry_run=False, limit=steamdb_limit)
    except Exception as exc:
        logger.error("SteamDB update failed: %s", exc)
        errors.append(str(exc))

    logger.info("Daily update: YouTube (new games only)...")
    try:
        from ingestors.youtube_ingestor import run as youtube_run
        youtube_limit = 25 if free_tier_mode else None
        youtube_run(dry_run=False, force=False, limit=youtube_limit)
    except Exception as exc:
        logger.error("YouTube update failed: %s", exc)
        errors.append(str(exc))

    logger.info("Daily update: Reddit (new games only)...")
    try:
        from ingestors.reddit_ingestor import run as reddit_run
        reddit_limit = 20 if free_tier_mode else None
        reddit_run(dry_run=False, force=False, limit=reddit_limit)
    except Exception as exc:
        logger.error("Reddit update failed: %s", exc)
        errors.append(str(exc))

    if run_retention:
        logger.info("Daily update: applying retention cleanup...")
        try:
            from ingestors.utils import apply_sql_file
            apply_sql_file("database/maintenance/001_free_tier_retention.sql")
        except Exception as exc:
            logger.error("Retention cleanup failed: %s", exc)
            errors.append(str(exc))

    elapsed = time.time() - start
    mins, secs = divmod(int(elapsed), 60)
    if errors:
        logger.warning(
            "Daily update finished with non-fatal errors in %dm %ds (count=%d).",
            mins,
            secs,
            len(errors),
        )
        logger.warning("Error summary: %s", " | ".join(errors[:5]))
    else:
        logger.info("Daily update complete in %dm %ds.", mins, secs)


if __name__ == "__main__":
    run()
