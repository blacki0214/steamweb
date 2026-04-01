from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base

# Default to local sqlite for zero-config development; override with DATABASE_URL for Postgres.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./indie_games.db").strip()

# Supabase often provides postgresql:// URLs; this app uses psycopg v3 driver.
if DATABASE_URL.startswith("postgresql://"):
	DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args: dict[str, object] = {}
if DATABASE_URL.startswith("sqlite"):
	connect_args["check_same_thread"] = False
elif DATABASE_URL.startswith("postgresql+psycopg://"):
	# Supabase pooler (PgBouncer) is incompatible with psycopg auto-prepared statements.
	connect_args["prepare_threshold"] = None

engine = create_engine(
	DATABASE_URL,
	echo=False,
	connect_args=connect_args,
	pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
	from app.db import models  # noqa: F401

	Base.metadata.create_all(bind=engine)
