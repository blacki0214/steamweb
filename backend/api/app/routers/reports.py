from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import os
import re
from typing import Any

from fastapi import APIRouter, Depends
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.security import require_bot_auth
from app.db.session import SessionLocal

router = APIRouter(dependencies=[Depends(require_bot_auth)])

FEATURED_CAT_URL = "https://store.steampowered.com/api/featuredcategories"
STEAMDB_CHARTS_URL = "https://steamdb.info/charts/"
STEAMDB_USER_AGENT = os.getenv("STEAMDB_USER_AGENT", "steamweb-bot/1.0 (+https://steamdb.info/charts/)")


def _normalize_chart_type(value: str) -> str:
    value_l = value.lower()
    if "most_played" in value_l or "most played" in value_l or "playing" in value_l or "concurrent" in value_l:
        return "most_played"
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
                        g.price_usd,
                        g.is_free,
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
        raw_price = row.get("price_usd")
        price_usd = float(raw_price) if raw_price is not None else None

        out[app_id] = {
            "name": str(row.get("name") or f"app_{app_id}"),
            "release_date": row.get("release_date"),
            "steam": {
            "price_usd": price_usd,
                "is_free": bool(row.get("is_free") or False),
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


def _parse_int_value(raw: Any) -> int | None:
    text_value = str(raw or "")
    cleaned = re.sub(r"[^0-9-]", "", text_value)
    if not cleaned or cleaned == "-":
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _extract_app_id(href: str) -> int | None:
    match = re.search(r"/app/(\d+)", href or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _infer_chart_type_from_table(table: Any) -> str:
    candidates: list[str] = []

    table_id = table.get("id")
    if table_id:
        candidates.append(str(table_id))

    classes = table.get("class", [])
    if classes:
        candidates.append(" ".join(classes))

    heading = table.find_previous(["h1", "h2", "h3", "h4"])
    if heading:
        candidates.append(heading.get_text(" ", strip=True))

    return " ".join(candidates).lower()


def _parse_live_rows(table: Any, limit: int) -> list[dict[str, Any]]:
    rows_out: list[dict[str, Any]] = []
    rows = table.select("tbody tr") or table.select("tr")

    for tr in rows:
        app_link = tr.select_one('a[href*="/app/"]')
        if app_link is None:
            continue

        app_id = _extract_app_id(str(app_link.get("href") or ""))
        name = str(app_link.get_text(" ", strip=True) or "Unknown")

        cells = tr.find_all("td")
        if not cells:
            continue

        rank = _parse_int_value(cells[0].get_text(" ", strip=True))
        if rank is None:
            rank = len(rows_out) + 1

        metrics: list[int] = []
        for td in cells[1:]:
            data_sort = td.get("data-sort")
            parsed = _parse_int_value(data_sort if data_sort is not None else td.get_text(" ", strip=True))
            if parsed is not None:
                metrics.append(parsed)

        rows_out.append(
            {
                "rank": rank,
                "app_id": app_id,
                "name": name,
                "players_current": metrics[0] if len(metrics) >= 1 else None,
                "players_peak_24h": metrics[1] if len(metrics) >= 2 else None,
                "players_all_time_peak": metrics[2] if len(metrics) >= 3 else None,
                "snapshot_at": datetime.now(timezone.utc),
            }
        )

        if len(rows_out) >= limit:
            break

    return rows_out


def _live_chart_blocks(limit: int) -> dict[str, list[dict[str, Any]]]:
    headers = {
        "User-Agent": STEAMDB_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://steamdb.info/",
        "Cache-Control": "no-cache",
    }
    try:
        resp = httpx.get(STEAMDB_CHARTS_URL, headers=headers, timeout=20)
        resp.raise_for_status()
    except Exception:
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")
    target_types = {"most_played", "trending", "hot_releases", "popular_releases"}
    raw_by_type: dict[str, list[dict[str, Any]]] = {}

    for table in soup.select("table"):
        normalized = _normalize_chart_type(_infer_chart_type_from_table(table))
        if normalized not in target_types:
            continue
        if normalized in raw_by_type:
            continue

        parsed_rows = _parse_live_rows(table, limit)
        if parsed_rows:
            raw_by_type[normalized] = parsed_rows

    all_ids: list[int] = []
    for items in raw_by_type.values():
        for row in items:
            app_id = row.get("app_id")
            if isinstance(app_id, int):
                all_ids.append(app_id)

    enrich = _enrich_games(sorted(set(all_ids)))
    out: dict[str, list[dict[str, Any]]] = {}
    for chart_type, rows in raw_by_type.items():
        mapped: list[dict[str, Any]] = []
        for row in rows[:limit]:
            app_id = row.get("app_id")
            extra = enrich.get(app_id) if isinstance(app_id, int) else None
            mapped.append(
                {
                    "rank": int(row.get("rank") or 0),
                    "app_id": app_id if isinstance(app_id, int) else None,
                    "name": (extra or {}).get("name") or str(row.get("name") or "Unknown"),
                    "players_current": row.get("players_current"),
                    "players_peak_24h": row.get("players_peak_24h"),
                    "players_all_time_peak": row.get("players_all_time_peak"),
                    "steam_store_url": (
                        f"https://store.steampowered.com/app/{app_id}"
                        if isinstance(app_id, int)
                        else None
                    ),
                    "steam_reviews": (extra or {}).get("steam", {}),
                    "reddit": (extra or {}).get("reddit", {}),
                    "youtube": (extra or {}).get("youtube", {}),
                    "snapshot_at": row.get("snapshot_at"),
                }
            )
        out[chart_type] = mapped

    return out


def _rows_signature(rows: list[dict[str, Any]], size: int = 5) -> tuple[tuple[int | None, int], ...]:
    signature: list[tuple[int | None, int]] = []
    for row in rows[:size]:
        app_id = row.get("app_id")
        rank_raw = row.get("rank")
        rank = int(rank_raw) if isinstance(rank_raw, int) else 0
        signature.append((app_id if isinstance(app_id, int) else None, rank))
    return tuple(signature)


def _latest_snapshot_iso(rows: list[dict[str, Any]]) -> str | None:
    latest: datetime | None = None
    for row in rows:
        snapshot = row.get("snapshot_at")
        if isinstance(snapshot, datetime):
            if latest is None or snapshot > latest:
                latest = snapshot
    if latest is None:
        return None
    return latest.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _realtime_quality_reason(
    section: str,
    rows: list[dict[str, Any]],
    *,
    limit: int,
    most_played_live_sig: tuple[tuple[int | None, int], ...],
) -> str | None:
    min_rows = max(1, min(3, limit))
    if len(rows) < min_rows:
        return "insufficient_rows"

    if section == "trending" and most_played_live_sig:
        if _rows_signature(rows) == most_played_live_sig:
            return "same_as_most_played"

    return None


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


def _fallback_new_games_blocks(limit: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        resp = httpx.get(
            FEATURED_CAT_URL,
            params={"cc": "us", "l": "english"},
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("new_releases", {}).get("items", [])
    except Exception:
        return [], []

    out: list[dict[str, Any]] = []
    for idx, item in enumerate(items[:limit], start=1):
        app_id = item.get("id")
        app_id_int = int(app_id) if isinstance(app_id, int) else None
        name = str(item.get("name") or f"app_{app_id}")
        out.append(
            {
                "rank": idx,
                "app_id": app_id_int,
                "name": name,
                "release_date": "unknown",
                "steam_store_url": (
                    f"https://store.steampowered.com/app/{app_id_int}"
                    if app_id_int is not None
                    else None
                ),
                "steam_reviews": {},
                "reddit": {},
                "youtube": {},
            }
        )

    if not out:
        return [], []

    # Steam store fallback does not provide exact release date reliably.
    return out, out[: min(5, len(out))]


@router.get("/daily-steam")
def get_daily_steam_digest(limit: int = 10, realtime: bool = False) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 10))

    target_chart_sections = ["most_played", "trending", "hot_releases", "popular_releases"]
    chart_rows: dict[str, list[dict[str, Any]]] = {}
    chart_meta: dict[str, dict[str, Any]] = {}

    if realtime:
        live_rows_by_section = _live_chart_blocks(safe_limit)
        live_most_played_sig = _rows_signature(live_rows_by_section.get("most_played", []))

        for section in target_chart_sections:
            rows = live_rows_by_section.get(section, [])
            if not rows:
                chart_meta[section] = {
                    "source": "live_steamdb_missing",
                    "snapshot_at": None,
                    "quality": "missing",
                }
                continue

            quality_reason = _realtime_quality_reason(
                section,
                rows,
                limit=safe_limit,
                most_played_live_sig=live_most_played_sig,
            )
            if quality_reason:
                chart_meta[section] = {
                    "source": "live_steamdb_rejected",
                    "snapshot_at": _latest_snapshot_iso(rows),
                    "quality": quality_reason,
                }
                continue

            chart_rows[section] = rows
            chart_meta[section] = {
                "source": "live_steamdb",
                "snapshot_at": _latest_snapshot_iso(rows),
                "quality": "accepted",
            }

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
        if normalized not in set(target_chart_sections):
            continue
        if normalized in chart_rows:
            continue
        db_rows = _chart_block(str(raw_chart_type), safe_limit)
        if not db_rows:
            chart_meta.setdefault(
                normalized,
                {
                    "source": "db_snapshot_empty",
                    "snapshot_at": None,
                    "quality": "empty",
                },
            )
            continue

        chart_rows[normalized] = db_rows
        chart_meta[normalized] = {
            "source": "db_snapshot",
            "snapshot_at": _latest_snapshot_iso(db_rows),
            "quality": "accepted",
        }

    most_played_rows = chart_rows.get("most_played", [])
    trending_rows = chart_rows.get("trending", [])
    popular_rows = chart_rows.get("popular_releases", [])

    # Avoid showing duplicated sections when source data mirrors another chart.
    if trending_rows and most_played_rows and _rows_signature(trending_rows) == _rows_signature(most_played_rows):
        trending_rows = []
        chart_meta["trending"] = {
            "source": "duplicate_filtered",
            "snapshot_at": _latest_snapshot_iso(chart_rows.get("trending", [])),
            "quality": "same_as_most_played",
        }

    hot_direct_rows = chart_rows.get("hot_releases", [])
    if hot_direct_rows and popular_rows and _rows_signature(hot_direct_rows) == _rows_signature(popular_rows):
        hot_direct_rows = []
        chart_meta["hot_releases"] = {
            "source": "duplicate_filtered",
            "snapshot_at": _latest_snapshot_iso(chart_rows.get("hot_releases", [])),
            "quality": "same_as_popular_releases",
        }

    if hot_direct_rows:
        hot_rows = hot_direct_rows
        hot_meta = chart_meta.get(
            "hot_releases",
            {"source": "unknown", "snapshot_at": _latest_snapshot_iso(hot_rows), "quality": "accepted"},
        )
    elif popular_rows:
        hot_rows = popular_rows
        hot_meta = {
            "source": "fallback_from_popular_releases",
            "snapshot_at": _latest_snapshot_iso(hot_rows),
            "quality": "fallback",
        }
    elif most_played_rows:
        hot_rows = most_played_rows
        hot_meta = {
            "source": "fallback_from_most_played",
            "snapshot_at": _latest_snapshot_iso(hot_rows),
            "quality": "fallback",
        }
    else:
        hot_rows = []
        hot_meta = {
            "source": "missing",
            "snapshot_at": None,
            "quality": "empty",
        }

    new_this_week, releases_today = _new_games_blocks(safe_limit)
    new_source = "db_release_calendar"
    if not new_this_week and not releases_today:
        new_this_week, releases_today = _fallback_new_games_blocks(safe_limit)
        new_source = "steam_store_featured_fallback"

    section_meta = {
        "most_played_games": chart_meta.get(
            "most_played",
            {"source": "missing", "snapshot_at": _latest_snapshot_iso(most_played_rows), "quality": "empty"},
        ),
        "trending_games": chart_meta.get(
            "trending",
            {"source": "missing", "snapshot_at": _latest_snapshot_iso(trending_rows), "quality": "empty"},
        ),
        "hot_releases": hot_meta,
        "popular_releases": chart_meta.get(
            "popular_releases",
            {"source": "missing", "snapshot_at": _latest_snapshot_iso(popular_rows), "quality": "empty"},
        ),
        "new_games_this_week": {
            "source": new_source,
            "snapshot_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "quality": "accepted" if new_this_week else "empty",
        },
        "releases_today": {
            "source": new_source,
            "snapshot_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "quality": "accepted" if releases_today else "empty",
        },
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_10": {
            "most_played_games": most_played_rows,
            "trending_games": trending_rows,
            "hot_releases": hot_rows,
            "popular_releases": popular_rows,
            "new_games_this_week": new_this_week,
            "releases_today": releases_today,
        },
        "section_meta": section_meta,
    }
