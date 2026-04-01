"""Shared utilities for data-pipeline ingestors."""

import os
import time
import logging
from contextlib import contextmanager
from typing import Iterator
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from psycopg2.extensions import connection as PgConnection

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_connection() -> PgConnection:
    """Return a new psycopg2 connection using environment variables."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    sslmode = os.getenv("POSTGRES_SSLMODE", "")
    sslrootcert = os.getenv("POSTGRES_SSLROOTCERT", "")

    if database_url:
        kwargs: dict[str, str] = {}
        if sslmode and "sslmode=" not in database_url:
            kwargs["sslmode"] = sslmode
        if sslrootcert:
            kwargs["sslrootcert"] = sslrootcert
        return psycopg2.connect(database_url, **kwargs)

    kwargs = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "dbname": os.getenv("POSTGRES_DB", "indie_games"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    }
    if sslmode:
        kwargs["sslmode"] = sslmode
    if sslrootcert:
        kwargs["sslrootcert"] = sslrootcert
    return psycopg2.connect(**kwargs)


def log_database_target() -> None:
    """Log a safe DB target summary to verify runtime is pointed correctly."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlparse(database_url)
        host = parsed.hostname or "unknown-host"
        db_name = (parsed.path or "").lstrip("/") or "unknown-db"
        logger.info("Database target: host=%s db=%s (via DATABASE_URL)", host, db_name)
        return

    host = os.getenv("POSTGRES_HOST", "localhost")
    db_name = os.getenv("POSTGRES_DB", "indie_games")
    logger.info("Database target: host=%s db=%s (via POSTGRES_* env)", host, db_name)


def assert_database_ready() -> None:
    """Fail fast if DB is unreachable so cloud runs surface misconfigured targets early."""
    log_database_target()
    with db_cursor() as cur:
        cur.execute("SELECT 1")


@contextmanager
def db_cursor() -> Iterator[psycopg2.extras.RealDictCursor]:
    """Context manager: yields a cursor and auto-commits/closes."""
    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur
    finally:
        conn.close()


def rate_sleep(seconds: float = 1.5) -> None:
    """Polite delay between API calls."""
    time.sleep(seconds)
