"""
SteamDB Ingestor
================
Scrapes SteamDB charts to capture trending/hot game snapshots.

Source:
  - charts page: https://steamdb.info/charts/

Run:
    python -m ingestors.steamdb_ingestor
    python -m ingestors.steamdb_ingestor --dry-run
    python -m ingestors.steamdb_ingestor --limit 25
"""

import argparse
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from psycopg2.extras import Json

from ingestors.utils import db_cursor, rate_sleep

load_dotenv()
logger = logging.getLogger(__name__)

CHARTS_URL = "https://steamdb.info/charts/"
MOST_PLAYED_URL = "https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/"
FEATURED_CAT_URL = "https://store.steampowered.com/api/featuredcategories"
REQUEST_TIMEOUT = 20
DEFAULT_LIMIT_PER_CHART = 50
USER_AGENT = os.getenv("STEAMDB_USER_AGENT", "steamweb-bot/1.0 (+https://steamdb.info/charts/)")

INSERT_SNAPSHOT_SQL = """
INSERT INTO steamdb_chart_snapshots (
    snapshot_at,
    chart_type,
    rank,
    app_id,
    game_name,
    players_current,
    players_peak_24h,
    players_all_time_peak,
    raw_metrics,
    source_url
)
VALUES (
    %(snapshot_at)s,
    %(chart_type)s,
    %(rank)s,
    %(app_id)s,
    %(game_name)s,
    %(players_current)s,
    %(players_peak_24h)s,
    %(players_all_time_peak)s,
    %(raw_metrics)s,
    %(source_url)s
);
"""

CREATE_SNAPSHOT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS steamdb_chart_snapshots (
    id BIGSERIAL PRIMARY KEY,
    snapshot_at TIMESTAMPTZ NOT NULL,
    chart_type TEXT NOT NULL,
    rank INTEGER NOT NULL,
    app_id INTEGER,
    game_name TEXT NOT NULL,
    players_current INTEGER,
    players_peak_24h INTEGER,
    players_all_time_peak INTEGER,
    raw_metrics JSONB,
    source_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_steamdb_snapshots_snapshot_at
ON steamdb_chart_snapshots(snapshot_at);

CREATE INDEX IF NOT EXISTS idx_steamdb_snapshots_chart_rank
ON steamdb_chart_snapshots(chart_type, rank);

CREATE INDEX IF NOT EXISTS idx_steamdb_snapshots_app_id
ON steamdb_chart_snapshots(app_id);
"""


def fetch_charts_html() -> str:
    """Download SteamDB charts page HTML."""
    # SteamDB can be strict with bot traffic; send browser-like headers.
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://steamdb.info/",
        "Cache-Control": "no-cache",
    }
    resp = requests.get(
        CHARTS_URL,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.text


def fetch_fallback_rows(limit_per_chart: int) -> list[dict]:
    """Fallback when SteamDB blocks requests: use official Steam chart endpoints."""
    snapshot_at = datetime.now(timezone.utc)
    out: list[dict] = []

    try:
        resp = requests.get(MOST_PLAYED_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        ranks = resp.json().get("response", {}).get("ranks", [])[:limit_per_chart]

        for idx, item in enumerate(ranks, start=1):
            app_id = item.get("appid")
            current = item.get("peak_in_game")
            out.append(
                {
                    "snapshot_at": snapshot_at,
                    "chart_type": "most_played_fallback",
                    "rank": int(item.get("rank") or idx),
                    "app_id": int(app_id) if app_id is not None else None,
                    "game_name": str(item.get("name") or f"app_{app_id}"),
                    "players_current": int(current) if current is not None else None,
                    "players_peak_24h": None,
                    "players_all_time_peak": None,
                    "raw_metrics": {"source": "steamcharts_api"},
                    "source_url": MOST_PLAYED_URL,
                }
            )
    except Exception as exc:
        logger.warning("Fallback most-played fetch failed: %s", exc)

    try:
        resp = requests.get(
            FEATURED_CAT_URL,
            params={"cc": "us", "l": "english"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get("top_sellers", {}).get("items", [])[:limit_per_chart]

        for idx, item in enumerate(items, start=1):
            app_id = item.get("id")
            out.append(
                {
                    "snapshot_at": snapshot_at,
                    "chart_type": "top_sellers_fallback",
                    "rank": idx,
                    "app_id": int(app_id) if app_id is not None else None,
                    "game_name": str(item.get("name") or f"app_{app_id}"),
                    "players_current": None,
                    "players_peak_24h": None,
                    "players_all_time_peak": None,
                    "raw_metrics": {"source": "featured_categories"},
                    "source_url": FEATURED_CAT_URL,
                }
            )
    except Exception as exc:
        logger.warning("Fallback top-sellers fetch failed: %s", exc)

    return out


def parse_int(text: str) -> Optional[int]:
    """Extract first integer from text like '#12', '123,456', or '1 234'."""
    if not text:
        return None
    cleaned = re.sub(r"[^0-9-]", "", text)
    if not cleaned or cleaned == "-":
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def extract_app_id_from_href(href: str) -> Optional[int]:
    """Extract app id from href like '/app/570/' or full URL."""
    if not href:
        return None
    match = re.search(r"/app/(\d+)", href)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def infer_chart_type(table) -> str:
    """Infer chart type from table id/class and nearest heading text."""
    candidates: list[str] = []

    table_id = table.get("id")
    if table_id:
        candidates.append(str(table_id))

    class_list = table.get("class", [])
    if class_list:
        candidates.append(" ".join(class_list))

    heading = table.find_previous(["h1", "h2", "h3", "h4"])
    if heading:
        candidates.append(heading.get_text(" ", strip=True))

    blob = " ".join(candidates).lower()

    if "trending" in blob:
        return "trending"
    if "hot" in blob:
        return "hot"
    if "playing" in blob or "concurrent" in blob:
        return "most_played"
    if "seller" in blob or "grossing" in blob or "revenue" in blob:
        return "top_sellers"
    if "popular" in blob:
        return "popular"
    return "chart"


def parse_table_rows(table, chart_type: str, limit: int) -> list[dict]:
    """Parse one table into normalized snapshot rows."""
    rows_out: list[dict] = []
    body_rows = table.select("tbody tr") or table.select("tr")

    for tr in body_rows:
        app_link = tr.select_one('a[href*="/app/"]')
        if not app_link:
            continue

        app_id = extract_app_id_from_href(app_link.get("href", ""))
        game_name = app_link.get_text(" ", strip=True)
        if not game_name:
            continue

        cells = tr.find_all("td")
        if not cells:
            continue

        rank = parse_int(cells[0].get_text(" ", strip=True))
        if rank is None:
            rank = len(rows_out) + 1

        metrics: list[int] = []
        for td in cells[1:]:
            data_sort = td.get("data-sort")
            if data_sort is not None:
                parsed_sort = parse_int(str(data_sort))
                if parsed_sort is not None:
                    metrics.append(parsed_sort)
                    continue

            parsed_text = parse_int(td.get_text(" ", strip=True))
            if parsed_text is not None:
                metrics.append(parsed_text)

        players_current = metrics[0] if len(metrics) >= 1 else None
        players_peak_24h = metrics[1] if len(metrics) >= 2 else None
        players_all_time_peak = metrics[2] if len(metrics) >= 3 else None

        raw_metrics = {f"metric_{idx + 1}": value for idx, value in enumerate(metrics)}

        rows_out.append(
            {
                "snapshot_at": datetime.now(timezone.utc),
                "chart_type": chart_type,
                "rank": rank,
                "app_id": app_id,
                "game_name": game_name,
                "players_current": players_current,
                "players_peak_24h": players_peak_24h,
                "players_all_time_peak": players_all_time_peak,
                "raw_metrics": raw_metrics,
                "source_url": CHARTS_URL,
            }
        )

        if len(rows_out) >= limit:
            break

    return rows_out


def parse_charts(html: str, limit_per_chart: int) -> list[dict]:
    """Parse all chart tables from SteamDB charts page."""
    soup = BeautifulSoup(html, "html.parser")
    all_rows: list[dict] = []
    seen_keys: set[tuple[str, int, Optional[int], str]] = set()

    for table in soup.select("table"):
        if not table.select_one('a[href*="/app/"]'):
            continue

        chart_type = infer_chart_type(table)
        parsed_rows = parse_table_rows(table, chart_type=chart_type, limit=limit_per_chart)

        for row in parsed_rows:
            dedupe_key = (row["chart_type"], row["rank"], row["app_id"], row["game_name"])
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            all_rows.append(row)

    return all_rows


def save_rows(rows: list[dict]) -> None:
    """Persist all snapshot rows to DB."""
    with db_cursor() as cur:
        cur.execute(CREATE_SNAPSHOT_TABLE_SQL)
        for row in rows:
            payload = {**row, "raw_metrics": Json(row["raw_metrics"])}
            cur.execute(INSERT_SNAPSHOT_SQL, payload)


def hydrate_game_names_from_db(rows: list[dict]) -> None:
    """Fill fallback game names from local games table when possible."""
    app_ids = [
        row["app_id"]
        for row in rows
        if row.get("app_id") is not None and str(row.get("game_name", "")).startswith("app_")
    ]
    if not app_ids:
        return

    lookup: dict[int, str] = {}
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT id, name FROM games WHERE id = ANY(%s)",
                (app_ids,),
            )
            for record in cur.fetchall():
                lookup[int(record["id"])] = str(record["name"])
    except Exception as exc:
        logger.debug("Name hydration skipped: %s", exc)
        return

    for row in rows:
        app_id = row.get("app_id")
        if app_id in lookup and str(row.get("game_name", "")).startswith("app_"):
            row["game_name"] = lookup[app_id]


def run(dry_run: bool = False, limit: Optional[int] = None) -> None:
    limit_per_chart = limit or DEFAULT_LIMIT_PER_CHART
    logger.info("SteamDB ingestor starting | limit_per_chart=%s | dry_run=%s", limit_per_chart, dry_run)

    rows: list[dict] = []
    try:
        html = fetch_charts_html()
        rate_sleep(0.5)
        rows = parse_charts(html, limit_per_chart=limit_per_chart)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        logger.warning(
            "SteamDB charts request failed with status=%s; using fallback endpoints.",
            status,
        )
        rows = fetch_fallback_rows(limit_per_chart=limit_per_chart)
    except Exception as exc:
        logger.warning("SteamDB scrape failed: %s. Using fallback endpoints.", exc)
        rows = fetch_fallback_rows(limit_per_chart=limit_per_chart)

    if not rows:
        logger.warning("No SteamDB chart rows parsed. Page structure may have changed.")
        return

    hydrate_game_names_from_db(rows)

    logger.info("Parsed %d SteamDB chart rows", len(rows))

    if dry_run:
        payload = [
            {
                **row,
                "snapshot_at": row["snapshot_at"].isoformat(),
            }
            for row in rows
        ]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    save_rows(rows)
    logger.info("SteamDB ingestor done. Saved %d rows.", len(rows))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SteamDB trending/hot charts ingestor")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON, skip DB writes")
    parser.add_argument("--limit", type=int, default=None, help="Max rows per chart table")
    args = parser.parse_args()

    run(dry_run=args.dry_run, limit=args.limit)
