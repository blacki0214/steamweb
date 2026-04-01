from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.security import require_bot_auth
from app.db.session import SessionLocal

router = APIRouter(dependencies=[Depends(require_bot_auth)])


def _normalize_chart_type(value: str) -> str:
    value_l = value.lower()
    if "trending" in value_l:
        return "trending"
    if "hot" in value_l:
        return "hot_releases"
    if "popular" in value_l or "seller" in value_l:
        return "popular_releases"
    return value_l


def _parse_release_date(raw: str) -> date | None:
    cleaned = (raw or "").strip().replace("st", "").replace("nd", "").replace("rd", "").replace("th", "")
    if not cleaned:
        return None

    formats = [
        "%d %b, %Y",
        "%b %d, %Y",
        "%b %Y",
        "%d %B, %Y",
        "%B %d, %Y",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _enrich_games(app_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not app_ids:
        return {}

    try:
        with SessionLocal() as db:
            rows = db.execute(
                text(
                    """
                    SELECT
                        g.id AS app_id,
                        g.name,
                        g.release_date,
                        g.total_reviews,
                        g.positive_reviews,
                        (
                            SELECT y.video_id
                            FROM youtube_videos y
                            WHERE y.app_id = g.id
                            ORDER BY y.view_count DESC NULLS LAST, y.published_at DESC NULLS LAST
                            LIMIT 1
                        ) AS top_video_id,
                        COALESCE(rp.reddit_posts, 0) AS reddit_posts,
                        COALESCE(rp.reddit_score_sum, 0) AS reddit_score_sum,
                        COALESCE(sr.steam_review_samples, 0) AS steam_review_samples,
                        COALESCE(sr.steam_positive_ratio, 0) AS steam_positive_ratio
                    FROM games g
                    LEFT JOIN (
                        SELECT app_id, COUNT(*) AS reddit_posts, COALESCE(SUM(score), 0) AS reddit_score_sum
                        FROM reddit_posts
                        GROUP BY app_id
                    ) rp ON rp.app_id = g.id
                    LEFT JOIN (
                        SELECT
                            app_id,
                            COUNT(*) AS steam_review_samples,
                            COALESCE(AVG(CASE WHEN voted_up THEN 1.0 ELSE 0.0 END), 0) AS steam_positive_ratio
                        FROM steam_reviews
                        GROUP BY app_id
                    ) sr ON sr.app_id = g.id
                    WHERE g.id = ANY(:app_ids)
                    """
                ),
                {"app_ids": app_ids},
            ).mappings().all()
    except SQLAlchemyError:
        return {}

    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        app_id = int(row["app_id"])
        video_id = row.get("top_video_id")
        out[app_id] = {
            "name": str(row.get("name") or f"app_{app_id}"),
            "release_date": row.get("release_date"),
            "steam": {
                "total_reviews": int(row.get("total_reviews") or 0),
                "positive_reviews": int(row.get("positive_reviews") or 0),
                "review_samples": int(row.get("steam_review_samples") or 0),
                "positive_ratio": float(row.get("steam_positive_ratio") or 0),
            },
            "reddit": {
                "posts": int(row.get("reddit_posts") or 0),
                "score_sum": int(row.get("reddit_score_sum") or 0),
            },
            "youtube": {
                "video_url": (
                    f"https://www.youtube.com/watch?v={video_id}"
                    if isinstance(video_id, str) and video_id
                    else None
                )
            },
        }
    return out


def _chart_block(chart_type: str, limit: int) -> list[dict[str, Any]]:
    try:
        with SessionLocal() as db:
            rows = db.execute(
                text(
                    """
                    WITH latest AS (
                        SELECT MAX(snapshot_at) AS latest_at
                        FROM steamdb_chart_snapshots
                        WHERE chart_type = :chart_type
                    )
                    SELECT
                        s.app_id,
                        s.game_name,
                        s.rank,
                        s.players_current,
                        s.players_peak_24h,
                        s.players_all_time_peak,
                        s.snapshot_at
                    FROM steamdb_chart_snapshots s
                    JOIN latest l ON s.snapshot_at = l.latest_at
                    WHERE s.chart_type = :chart_type
                    ORDER BY s.rank ASC
                    LIMIT :limit
                    """
                ),
                {"chart_type": chart_type, "limit": limit},
            ).mappings().all()
    except SQLAlchemyError:
        return []

    app_ids = [int(row["app_id"]) for row in rows if row.get("app_id") is not None]
    enrich = _enrich_games(app_ids)

    items: list[dict[str, Any]] = []
    for row in rows:
        app_id_raw = row.get("app_id")
        app_id = int(app_id_raw) if app_id_raw is not None else None
        extra = enrich.get(app_id) if app_id is not None else None

        items.append(
            {
                "rank": int(row["rank"]),
                "app_id": app_id,
                "name": (extra or {}).get("name") or str(row.get("game_name") or "Unknown"),
                "players_current": row.get("players_current"),
                "players_peak_24h": row.get("players_peak_24h"),
                "players_all_time_peak": row.get("players_all_time_peak"),
                "steam_store_url": (
                    f"https://store.steampowered.com/app/{app_id}"
                    if app_id is not None
                    else None
                ),
                "steam_reviews": (extra or {}).get("steam", {}),
                "reddit": (extra or {}).get("reddit", {}),
                "youtube": (extra or {}).get("youtube", {}),
                "snapshot_at": row.get("snapshot_at"),
            }
        )
    return items


def _new_games_blocks(limit: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        with SessionLocal() as db:
            rows = db.execute(
                text(
                    """
                    SELECT id, name, release_date
                    FROM games
                    WHERE release_date IS NOT NULL AND release_date <> ''
                    ORDER BY COALESCE(total_reviews, 0) DESC
                    LIMIT 2000
                    """
                )
            ).mappings().all()
    except SQLAlchemyError:
        return [], []

    today = datetime.now(timezone.utc).date()
    in_week: list[dict[str, Any]] = []
    today_list: list[dict[str, Any]] = []

    for row in rows:
        app_id = int(row["id"])
        parsed = _parse_release_date(str(row.get("release_date") or ""))
        if parsed is None:
            continue

        if today <= parsed <= today + timedelta(days=7):
            in_week.append({"app_id": app_id, "name": str(row.get("name") or f"app_{app_id}"), "release_date": parsed})
        if parsed == today:
            today_list.append({"app_id": app_id, "name": str(row.get("name") or f"app_{app_id}"), "release_date": parsed})

    in_week.sort(key=lambda x: x["release_date"])
    today_list.sort(key=lambda x: x["name"])

    def enrich_release(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        app_ids = [int(item["app_id"]) for item in items]
        enrich = _enrich_games(app_ids)
        out: list[dict[str, Any]] = []
        for idx, item in enumerate(items[:limit], start=1):
            app_id = int(item["app_id"])
            extra = enrich.get(app_id, {})
            out.append(
                {
                    "rank": idx,
                    "app_id": app_id,
                    "name": str(item["name"]),
                    "release_date": str(item["release_date"]),
                    "steam_store_url": f"https://store.steampowered.com/app/{app_id}",
                    "steam_reviews": extra.get("steam", {}),
                    "reddit": extra.get("reddit", {}),
                    "youtube": extra.get("youtube", {}),
                }
            )
        return out

    return enrich_release(in_week), enrich_release(today_list)


@router.get("/daily-steam")
def get_daily_steam_digest(limit: int = 10) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 10))

    chart_rows: dict[str, list[dict[str, Any]]] = {}
    try:
        with SessionLocal() as db:
            chart_types = db.execute(
                text(
                    """
                    SELECT DISTINCT chart_type
                    FROM steamdb_chart_snapshots
                    WHERE snapshot_at >= NOW() - INTERVAL '14 days'
                    """
                )
            ).scalars().all()
    except SQLAlchemyError:
        chart_types = []

    for raw_chart_type in chart_types:
        normalized = _normalize_chart_type(str(raw_chart_type))
        if normalized not in {"trending", "hot_releases", "popular_releases"}:
            continue
        if normalized in chart_rows:
            continue
        chart_rows[normalized] = _chart_block(str(raw_chart_type), safe_limit)

    new_this_week, releases_today = _new_games_blocks(safe_limit)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_10": {
            "trending_games": chart_rows.get("trending", []),
            "hot_releases": chart_rows.get("hot_releases", []),
            "popular_releases": chart_rows.get("popular_releases", []),
            "new_games_this_week": new_this_week,
            "releases_today": releases_today,
        },
    }
