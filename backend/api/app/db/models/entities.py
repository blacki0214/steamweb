from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OAuthState(Base):
    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    discord_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserConnection(Base):
    __tablename__ = "user_connections"

    discord_user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    steam_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserSteamStats(Base):
    __tablename__ = "user_steam_stats"

    discord_user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    steam_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    persona_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_games: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_playtime_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_games: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    discord_user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    steam_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    top_genres: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    mood_preferences: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    play_style: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecommendationSnapshot(Base):
    __tablename__ = "recommendation_snapshots"

    request_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    base_request_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    discord_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    game_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False)
    context: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
