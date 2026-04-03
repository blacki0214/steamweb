from __future__ import annotations

import json
import random
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select, text

from app.db.models import (
    FeedbackEvent,
    OAuthState,
    RecommendationSnapshot,
    UserConnection,
    UserProfileModel,
    UserSteamStats,
)
from app.db.session import SessionLocal, init_db
from app.schemas.contracts import (
    FeedbackRequest,
    GameDetailResponse,
    GameSearchItem,
    PriceInfo,
    RecommendationItem,
    RecommendationSources,
    RedditReviewInfo,
    ReviewSummaryInfo,
    SteamReviewInfo,
    UserProfile,
)
from app.services.steam_service import steam_realtime_service


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def to_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def to_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _normalize_label(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", cleaned)


def _extract_tag_values(raw: object) -> list[str]:
    values: list[str] = []

    if raw is None:
        return values

    if isinstance(raw, list):
        values.extend(str(item) for item in raw if str(item).strip())
    elif isinstance(raw, tuple | set):
        values.extend(str(item) for item in raw if str(item).strip())
    elif isinstance(raw, str):
        text_value = raw.strip()
        if not text_value:
            return values

        if text_value.startswith("[") or text_value.startswith("{"):
            try:
                parsed = json.loads(text_value)
                if isinstance(parsed, list):
                    values.extend(str(item) for item in parsed if str(item).strip())
                elif isinstance(parsed, dict):
                    values.extend(str(key) for key in parsed.keys() if str(key).strip())
                    values.extend(str(val) for val in parsed.values() if str(val).strip())
                return values
            except Exception:
                pass

        values.extend(part.strip() for part in re.split(r"[,;|]", text_value) if part.strip())
    else:
        text_value = str(raw).strip()
        if text_value:
            values.append(text_value)

    return values


def _build_normalized_tags(*raw_values: object) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        for value in _extract_tag_values(raw):
            token = _normalize_label(value)
            if token and token not in seen:
                seen.add(token)
                normalized.append(token)
    return normalized


MOOD_TAG_MAP: dict[str, list[str]] = {
    "chill": ["casual", "simulation", "indie", "adventure", "free to play", "puzzle"],
    "relaxing": ["casual", "simulation", "indie", "adventure", "free to play", "puzzle"],
    "intense": ["action", "rpg", "strategy", "sports", "racing", "pvp"],
    "dark": ["action", "rpg", "adventure", "survival", "atmospheric", "horror"],
    "story rich": ["rpg", "adventure", "indie", "simulation", "visual novel", "narrative"],
    "story-rich": ["rpg", "adventure", "indie", "simulation", "visual novel", "narrative"],
    "co op": ["co-op", "coop", "multiplayer", "online co-op", "action", "adventure"],
    "co-op": ["co-op", "coop", "multiplayer", "online co-op", "action", "adventure"],
    "competitive": ["competitive", "pvp", "ranked", "esports", "sports", "racing", "action"],
    "creative": ["simulation", "indie", "adventure", "sandbox", "building", "crafting"],
}


def _expand_mood_tokens(moods: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()

    for mood in moods:
        key = _normalize_label(mood)
        if not key:
            continue

        candidates = [key, *MOOD_TAG_MAP.get(key, [])]
        for candidate in candidates:
            token = _normalize_label(candidate)
            if not token or token in seen:
                continue
            seen.add(token)
            expanded.append(token)

    return expanded


NON_GAMEPLAY_TAGS: set[str] = {
    "single player",
    "singleplayer",
    "multi player",
    "multiplayer",
    "co op",
    "coop",
    "online co op",
    "online coop",
    "lan co op",
    "lan coop",
    "shared split screen",
    "sharedsplit screen",
    "shared split screen co op",
    "sharedsplit screen coop",
    "cross platform multiplayer",
    "crossplatform multiplayer",
    "mmo",
    "online pvp",
    "pvp",
    "online coop pvp",
    "steam achievements",
    "steamachievements",
    "steam trading cards",
    "steamtrading cards",
    "steam workshop",
    "steamworkshop",
    "steam cloud",
    "steamcloud",
    "family sharing",
    "familysharing",
    "remote play on phone",
    "remoteplay on phone",
    "remote play on tablet",
    "remoteplay on tablet",
    "remote play on tv",
    "remoteplay on tv",
    "remote play together",
    "remoteplay together",
    "partial controller support",
    "partial controller support",
    "full controller support",
    "tracked controller support",
    "vr supported",
    "includes level editor",
    "camera comfort",
    "adjustable text size",
    "adjustable difficulty",
    "custom volume controls",
    "mouse only option",
    "touch only option",
    "subtitle options",
    "stereo sound",
    "save anytime",
    "playable without timed input",
    "color alternatives",
    "stats",
    "valve anti cheat enabled",
}

DEFAULT_DISCOVERY_TAGS: list[str] = [
    "action",
    "adventure",
    "rpg",
    "strategy",
    "simulation",
    "survival",
    "puzzle",
    "platformer",
    "cozy",
    "roguelike",
]

LOCAL_FALLBACK_GAMES: list[dict[str, object]] = [
    {
        "appid": 1794680,
        "name": "Vampire Survivors",
        "tags": ["roguelike", "action", "indie", "bullet hell", "survival"],
        "price": 4.99,
        "is_free": False,
        "positive": 240000,
        "negative": 9000,
    },
    {
        "appid": 1942280,
        "name": "Brotato",
        "tags": ["roguelike", "action", "arena shooter", "indie"],
        "price": 4.99,
        "is_free": False,
        "positive": 65000,
        "negative": 4000,
    },
    {
        "appid": 1337520,
        "name": "Risk of Rain Returns",
        "tags": ["roguelike", "action", "platformer", "co-op"],
        "price": 14.99,
        "is_free": False,
        "positive": 19000,
        "negative": 2000,
    },
    {
        "appid": 548430,
        "name": "Deep Rock Galactic",
        "tags": ["action", "co-op", "shooter", "intense"],
        "price": 9.99,
        "is_free": False,
        "positive": 270000,
        "negative": 12000,
    },
]


def _filter_gameplay_tags(tags: list[str]) -> list[str]:
    filtered: list[str] = []
    for tag in tags:
        normalized = _normalize_label(tag)
        if normalized and normalized not in NON_GAMEPLAY_TAGS:
            filtered.append(normalized)
    return filtered


def _count_matches(wanted: list[str], tags: list[str]) -> int:
    if not wanted or not tags:
        return 0

    hits = 0
    for needle_raw in wanted:
        needle = _normalize_label(needle_raw)
        if not needle:
            continue
        if any(needle == tag or needle in tag for tag in tags):
            hits += 1
    return hits


class PersistentStore:
    def __init__(self) -> None:
        init_db()
        self._recent_recommendations_by_user: dict[str, list[str]] = {}
        self.games: list[GameDetailResponse] = [
            GameDetailResponse(
                game_id="steam_1145360",
                title="Hades",
                description="Battle out of hell in this rogue-like dungeon crawler.",
                genres=["Action", "Roguelike"],
                price=PriceInfo(amount=12.49, currency="USD", is_on_sale=True),
                youtube_video_url="https://www.youtube.com/watch?v=91t0ha9x0AE",
                steam_store_url="https://store.steampowered.com/app/1145360",
            ),
            GameDetailResponse(
                game_id="steam_413150",
                title="Stardew Valley",
                description="Farming, exploration, and cozy life simulation.",
                genres=["Cozy", "RPG", "Simulation"],
                price=PriceInfo(amount=14.99, currency="USD", is_on_sale=False),
                youtube_video_url="https://www.youtube.com/watch?v=ot7uXNQskhs",
                steam_store_url="https://store.steampowered.com/app/413150",
            ),
            GameDetailResponse(
                game_id="steam_367520",
                title="Hollow Knight",
                description="A challenging action-adventure in a vast ruined kingdom.",
                genres=["Metroidvania", "Action"],
                price=PriceInfo(amount=7.49, currency="USD", is_on_sale=True),
                youtube_video_url="https://www.youtube.com/watch?v=UAO2urG23S4",
                steam_store_url="https://store.steampowered.com/app/367520",
            ),
            GameDetailResponse(
                game_id="steam_632470",
                title="Disco Elysium",
                description="A groundbreaking detective RPG with deep narrative choices.",
                genres=["RPG", "Story Rich"],
                price=PriceInfo(amount=9.99, currency="USD", is_on_sale=False),
                youtube_video_url="https://www.youtube.com/watch?v=YV2lp6p_gXw",
                steam_store_url="https://store.steampowered.com/app/632470",
            ),
            GameDetailResponse(
                game_id="steam_646570",
                title="Slay the Spire",
                description="Deckbuilding roguelike with high replayability.",
                genres=["Roguelike", "Strategy", "Card Game"],
                price=PriceInfo(amount=8.49, currency="USD", is_on_sale=False),
                youtube_video_url="https://www.youtube.com/watch?v=9SZUtyYSOjQ",
                steam_store_url="https://store.steampowered.com/app/646570",
            ),
            GameDetailResponse(
                game_id="steam_105600",
                title="Terraria",
                description="Sandbox crafting adventure with co-op and exploration.",
                genres=["Sandbox", "Survival", "Co-op"],
                price=PriceInfo(amount=9.99, currency="USD", is_on_sale=False),
                youtube_video_url="https://www.youtube.com/watch?v=w7uOhFTrrq0",
                steam_store_url="https://store.steampowered.com/app/105600",
            ),
            GameDetailResponse(
                game_id="steam_892970",
                title="Valheim",
                description="Co-op survival crafting in a Viking-inspired world.",
                genres=["Survival", "Co-op", "Crafting"],
                price=PriceInfo(amount=19.99, currency="USD", is_on_sale=False),
                youtube_video_url="https://www.youtube.com/watch?v=LI7mCw5n0uM",
                steam_store_url="https://store.steampowered.com/app/892970",
            ),
            GameDetailResponse(
                game_id="steam_1245620",
                title="ELDEN RING",
                description="Open-world action RPG with challenging combat.",
                genres=["Action", "RPG", "Dark Fantasy"],
                price=PriceInfo(amount=39.99, currency="USD", is_on_sale=False),
                youtube_video_url="https://www.youtube.com/watch?v=K_03kFqWfqs",
                steam_store_url="https://store.steampowered.com/app/1245620",
            ),
            GameDetailResponse(
                game_id="steam_413410",
                title="Duskers",
                description="Atmospheric strategy survival with tense, dark mood.",
                genres=["Strategy", "Dark", "Survival"],
                price=PriceInfo(amount=19.99, currency="USD", is_on_sale=False),
                youtube_video_url="https://www.youtube.com/watch?v=5N8Q5Q4h7as",
                steam_store_url="https://store.steampowered.com/app/413410",
            ),
        ]

    def create_state(self, discord_user_id: str, redirect_uri: str) -> tuple[str, datetime]:
        state = f"st_{uuid4().hex[:18]}"
        expires_at = utc_now() + timedelta(minutes=15)
        with SessionLocal() as db:
            db.add(
                OAuthState(
                    state=state,
                    discord_user_id=discord_user_id,
                    redirect_uri=redirect_uri,
                    expires_at=expires_at,
                    created_at=utc_now(),
                )
            )
            db.commit()
        return state, expires_at

    def complete_oauth(self, state: str, steam_id: str) -> dict[str, object] | None:
        with SessionLocal() as db:
            row = db.execute(select(OAuthState).where(OAuthState.state == state)).scalar_one_or_none()
            if row is None or ensure_aware_utc(row.expires_at) < utc_now():
                return None

            discord_user_id = row.discord_user_id
            db.execute(delete(OAuthState).where(OAuthState.state == state))

            connection = db.execute(
                select(UserConnection).where(UserConnection.discord_user_id == discord_user_id)
            ).scalar_one_or_none()
            now = utc_now()
            if connection is None:
                connection = UserConnection(
                    discord_user_id=discord_user_id,
                    steam_id=steam_id,
                    connected_at=now,
                )
                db.add(connection)
            else:
                connection.steam_id = steam_id
                connection.connected_at = now

            profile = db.execute(
                select(UserProfileModel).where(UserProfileModel.discord_user_id == discord_user_id)
            ).scalar_one_or_none()
            if profile is None:
                profile = UserProfileModel(
                    discord_user_id=discord_user_id,
                    steam_connected=True,
                    top_genres=["roguelike", "metroidvania"],
                    mood_preferences=["intense", "story-rich"],
                    play_style={"session_minutes_preference": 60, "budget_preference": "low"},
                    updated_at=now,
                )
                db.add(profile)
            else:
                profile.steam_connected = True
                profile.updated_at = now

            db.commit()
            return {
                "steam_id": steam_id,
                "connected_at": now,
            }

    def get_oauth_state(self, state: str) -> dict[str, object] | None:
        with SessionLocal() as db:
            row = db.execute(select(OAuthState).where(OAuthState.state == state)).scalar_one_or_none()
            if row is None:
                return None
            return {
                "state": row.state,
                "discord_user_id": row.discord_user_id,
                "redirect_uri": row.redirect_uri,
                "expires_at": ensure_aware_utc(row.expires_at),
            }

    def get_connection(self, discord_user_id: str) -> dict[str, object] | None:
        with SessionLocal() as db:
            row = db.execute(
                select(UserConnection).where(UserConnection.discord_user_id == discord_user_id)
            ).scalar_one_or_none()
            if row is None:
                return None
            stats = db.execute(
                select(UserSteamStats).where(UserSteamStats.discord_user_id == discord_user_id)
            ).scalar_one_or_none()

            return {
                "steam_id": row.steam_id,
                "connected_at": row.connected_at,
                "persona_name": stats.persona_name if stats else None,
                "profile_url": stats.profile_url if stats else None,
                "avatar_url": stats.avatar_url if stats else None,
                "total_games": stats.total_games if stats else None,
                "total_playtime_hours": stats.total_playtime_hours if stats else None,
                "top_games": (stats.top_games or []) if stats else [],
                "synced_at": stats.synced_at if stats else None,
            }

    def upsert_steam_stats(
        self,
        discord_user_id: str,
        steam_id: str,
        profile: dict[str, str] | None,
        game_summary: dict[str, object] | None,
    ) -> None:
        with SessionLocal() as db:
            row = db.execute(
                select(UserSteamStats).where(UserSteamStats.discord_user_id == discord_user_id)
            ).scalar_one_or_none()

            if row is None:
                row = UserSteamStats(
                    discord_user_id=discord_user_id,
                    steam_id=steam_id,
                    synced_at=utc_now(),
                    top_games=[],
                )
                db.add(row)

            row.steam_id = steam_id
            if profile:
                row.persona_name = profile.get("persona_name")
                row.profile_url = profile.get("profile_url")
                row.avatar_url = profile.get("avatar_url")

            if game_summary:
                total_games = game_summary.get("total_games")
                total_playtime_hours = game_summary.get("total_playtime_hours")
                top_games = game_summary.get("top_games")

                row.total_games = to_int(total_games, default=0) if total_games is not None else None
                row.total_playtime_hours = (
                    to_float(total_playtime_hours, default=0.0)
                    if total_playtime_hours is not None
                    else None
                )
                row.top_games = top_games if isinstance(top_games, list) else []

            row.synced_at = utc_now()
            db.commit()

    def unlink_connection(self, discord_user_id: str) -> None:
        with SessionLocal() as db:
            db.execute(delete(UserConnection).where(UserConnection.discord_user_id == discord_user_id))
            db.execute(delete(UserSteamStats).where(UserSteamStats.discord_user_id == discord_user_id))
            profile = db.execute(
                select(UserProfileModel).where(UserProfileModel.discord_user_id == discord_user_id)
            ).scalar_one_or_none()
            if profile:
                profile.steam_connected = False
                profile.updated_at = utc_now()
            db.commit()

    def get_or_create_profile(self, discord_user_id: str) -> UserProfile:
        with SessionLocal() as db:
            row = db.execute(
                select(UserProfileModel).where(UserProfileModel.discord_user_id == discord_user_id)
            ).scalar_one_or_none()
            if row is None:
                row = UserProfileModel(
                    discord_user_id=discord_user_id,
                    steam_connected=self.get_connection(discord_user_id) is not None,
                    top_genres=[],
                    mood_preferences=[],
                    play_style={},
                    updated_at=utc_now(),
                )
                db.add(row)
                db.commit()

            return UserProfile(
                discord_user_id=row.discord_user_id,
                steam_connected=row.steam_connected,
                top_genres=row.top_genres or [],
                mood_preferences=row.mood_preferences or [],
                play_style=row.play_style or {},
                updated_at=row.updated_at,
            )

    def update_profile(self, profile: UserProfile) -> None:
        with SessionLocal() as db:
            row = db.execute(
                select(UserProfileModel).where(UserProfileModel.discord_user_id == profile.discord_user_id)
            ).scalar_one_or_none()
            if row is None:
                row = UserProfileModel(
                    discord_user_id=profile.discord_user_id,
                    steam_connected=profile.steam_connected,
                    top_genres=profile.top_genres,
                    mood_preferences=profile.mood_preferences,
                    play_style=profile.play_style,
                    updated_at=profile.updated_at,
                )
                db.add(row)
            else:
                row.steam_connected = profile.steam_connected
                row.top_genres = profile.top_genres
                row.mood_preferences = profile.mood_preferences
                row.play_style = profile.play_style
                row.updated_at = profile.updated_at
            db.commit()

    def build_recommendations(
        self,
        top_n: int,
        discord_user_id: str | None = None,
        genres: list[str] | None = None,
        moods: list[str] | None = None,
        max_price: float | None = None,
        relevance_mode: str = "medium",
    ) -> list[RecommendationItem]:
        db_first = self._build_recommendations_from_database(
            top_n=top_n,
            discord_user_id=discord_user_id,
            genres=genres or [],
            moods=moods or [],
            max_price=max_price,
            relevance_mode=relevance_mode,
        )
        if db_first:
            return db_first

        # Prefer real-time Steam data; fallback to local sample set for resilience.
        live = self._build_recommendations_from_live_data(
            top_n=top_n,
            discord_user_id=discord_user_id,
            genres=genres or [],
            moods=moods or [],
            max_price=max_price,
            relevance_mode=relevance_mode,
        )
        if live:
            return live

        fallback = self._build_recommendations_from_local_fallback(
            top_n=top_n,
            genres=genres or [],
            moods=moods or [],
            max_price=max_price,
            relevance_mode=relevance_mode,
        )
        if fallback:
            return fallback
        return []

    def _build_recommendations_from_database(
        self,
        top_n: int,
        discord_user_id: str | None,
        genres: list[str],
        moods: list[str],
        max_price: float | None,
        relevance_mode: str,
    ) -> list[RecommendationItem]:
        if SessionLocal.kw.get("bind") is None:
            return []

        steamdb_signals = self._load_steamdb_signals(limit=5000)

        try:
            with SessionLocal() as db:
                rows = db.execute(
                    text(
                        """
                        SELECT
                            g.id,
                            g.name,
                            COALESCE(g.short_description, g.description, '') AS description,
                            g.normalized_gameplay_tags,
                            g.genres,
                            g.tags,
                            COALESCE(g.price_usd, 0) AS price_usd,
                            COALESCE(g.is_free, false) AS is_free,
                            COALESCE(g.total_reviews, 0) AS total_reviews,
                            COALESCE(g.positive_reviews, 0) AS positive_reviews,
                            COALESCE(g.review_score_desc, 'Mixed') AS review_score_desc,
                            (
                                SELECT y.video_id
                                FROM youtube_videos y
                                WHERE y.app_id = g.id
                                ORDER BY y.view_count DESC NULLS LAST, y.published_at DESC NULLS LAST
                                LIMIT 1
                            ) AS top_video_id
                        FROM games g
                        ORDER BY COALESCE(g.positive_reviews, 0) DESC, COALESCE(g.total_reviews, 0) DESC
                        LIMIT :limit
                        """
                    ),
                    {
                        "limit": min(
                            max(top_n * (120 if genres else 20), 100),
                            500,
                        )
                    },
                ).mappings().all()
        except Exception:
            return []

        if not rows:
            return []

        wanted_genres = [_normalize_label(g) for g in genres if g.strip()]
        wanted_moods = _expand_mood_tokens(moods)

        strict_items: list[RecommendationItem] = []
        medium_items: list[RecommendationItem] = []
        broad_items: list[RecommendationItem] = []

        for row in rows:
            game_id = int(row["id"])
            title = str(row["name"])
            price = to_float(row.get("price_usd"), default=0.0)
            is_free = bool(row.get("is_free", False))
            if max_price is not None and not is_free and price > max_price:
                continue

            raw_normalized_tags = row.get("normalized_gameplay_tags")
            all_tags = _build_normalized_tags(raw_normalized_tags)
            tags = _filter_gameplay_tags(all_tags)
            if not tags:
                # Backward-compat for rows not normalized yet.
                all_tags = _build_normalized_tags(row.get("tags"), row.get("genres"))
                tags = _filter_gameplay_tags(all_tags)

            genre_hits = _count_matches(wanted_genres, tags)
            mood_hits = _count_matches(wanted_moods, all_tags)

            # Genre-selected requests should never return non-genre matches.
            if wanted_genres and genre_hits == 0:
                continue

            if (wanted_genres or wanted_moods) and (genre_hits + mood_hits == 0):
                continue

            total_reviews = to_int(row.get("total_reviews"), default=0)
            positive_reviews = to_int(row.get("positive_reviews"), default=0)
            popularity = max(0.0, min(float(positive_reviews) / 50000.0, 1.0))
            steamdb_signal = steamdb_signals.get(game_id, {})
            steamdb_boost = to_float(steamdb_signal.get("boost"), default=0.0)

            strict_match = True
            medium_match = True
            if wanted_genres and wanted_moods:
                strict_match = genre_hits > 0 and mood_hits > 0
                medium_match = genre_hits > 0
            elif wanted_genres:
                strict_match = genre_hits > 0
                medium_match = strict_match
            elif wanted_moods:
                strict_match = mood_hits > 0
                medium_match = strict_match

            strict_score = (genre_hits * 0.62) + (mood_hits * 0.20) + (popularity * 0.08) + (steamdb_boost * 0.10)
            medium_score = (genre_hits * 0.58) + (mood_hits * 0.20) + (popularity * 0.10) + (steamdb_boost * 0.12)
            broad_score = (genre_hits * 0.50) + (mood_hits * 0.15) + (popularity * 0.15) + (steamdb_boost * 0.20)

            positive_rate = (positive_reviews / total_reviews) if total_reviews > 0 else 0.0
            review_desc = str(row.get("review_score_desc") or "Mixed")
            video_id = row.get("top_video_id")
            youtube_url = (
                f"https://www.youtube.com/watch?v={video_id}"
                if isinstance(video_id, str) and video_id
                else f"https://www.youtube.com/results?search_query={title.replace(' ', '+')}+gameplay"
            )

            def make_item(score: float, tier: str) -> RecommendationItem:
                reasons = [f"Relevance tier: {tier}", "Data source: database"]
                if genre_hits > 0:
                    reasons.append("Matches your selected genre")
                if mood_hits > 0:
                    reasons.append("Matches your selected mood")
                if steamdb_boost > 0:
                    reasons.append("Hot/Popular on SteamDB")

                return RecommendationItem(
                    rank=1,
                    game_id=f"steam_{game_id}",
                    title=title,
                    price=PriceInfo(amount=0.0 if is_free else price, currency="USD", is_on_sale=False),
                    match_score=max(0.1, min(score, 0.99)),
                    reasons=reasons,
                    sources=RecommendationSources(
                        steam_store_url=f"https://store.steampowered.com/app/{game_id}",
                        youtube_video_url=youtube_url,
                        review_summary=ReviewSummaryInfo(
                            steam=SteamReviewInfo(label=review_desc, sample_size=total_reviews),
                            reddit=RedditReviewInfo(
                                sentiment_score=round(0.5 + (positive_rate * 0.45), 2),
                                highlights=["from scraped dataset", "db-ranked candidate"],
                            ),
                        ),
                    ),
                )

            if strict_match:
                strict_items.append(make_item(strict_score, "strict"))
            if medium_match:
                medium_items.append(make_item(medium_score, "medium"))
            broad_items.append(make_item(broad_score, "broad"))

        selected = self._fill_tiered_items(
            top_n=top_n,
            strict_items=strict_items,
            medium_items=medium_items,
            broad_items=broad_items,
            relevance_mode=relevance_mode,
        )
        selected = self._shuffle_within_top_pool(selected, pool_size=10)
        return self._apply_freshness_filter(discord_user_id=discord_user_id, items=selected, top_n=top_n)

    def _build_recommendations_from_local_fallback(
        self,
        top_n: int,
        genres: list[str],
        moods: list[str],
        max_price: float | None,
        relevance_mode: str,
    ) -> list[RecommendationItem]:
        wanted_genres = [_normalize_label(g) for g in genres if g.strip()]
        wanted_moods = _expand_mood_tokens(moods)

        scored_strict: list[tuple[float, RecommendationItem]] = []
        scored_medium: list[tuple[float, RecommendationItem]] = []
        scored_broad: list[tuple[float, RecommendationItem]] = []

        for game in LOCAL_FALLBACK_GAMES:
            price = to_float(game.get("price", 0.0), default=0.0)
            is_free = bool(game.get("is_free", False))
            if max_price is not None and not is_free and price > max_price:
                continue

            all_tags = _build_normalized_tags(game.get("tags", []))
            tags = _filter_gameplay_tags(all_tags)

            genre_hits = _count_matches(wanted_genres, tags)
            mood_hits = _count_matches(wanted_moods, all_tags)
            popularity = max(0.0, min(float(to_int(game.get("positive", 0), default=0)) / 50000.0, 1.0))

            if wanted_genres and genre_hits == 0:
                continue
            if (wanted_genres or wanted_moods) and (genre_hits + mood_hits == 0):
                continue

            strict_match = True
            medium_match = True
            if wanted_genres and wanted_moods:
                strict_match = genre_hits > 0 and mood_hits > 0
                medium_match = genre_hits > 0
            elif wanted_genres:
                strict_match = genre_hits > 0
                medium_match = strict_match
            elif wanted_moods:
                strict_match = mood_hits > 0
                medium_match = strict_match

            strict_score = (genre_hits * 0.75) + (mood_hits * 0.20) + (popularity * 0.05)
            medium_score = (genre_hits * 0.70) + (mood_hits * 0.20) + (popularity * 0.10)
            broad_score = (genre_hits * 0.60) + (mood_hits * 0.15) + (popularity * 0.25)

            def make_item(score: float, tier: str) -> RecommendationItem:
                appid = to_int(game.get("appid"), default=0)
                title = str(game.get("name") or f"Steam Game {appid}")
                positive = to_int(game.get("positive", 0), default=0)
                negative = to_int(game.get("negative", 0), default=0)
                total_reviews = max(positive + negative, 1)
                positive_rate = positive / total_reviews
                reasons = [f"Relevance tier: {tier}", "Data source: local fallback"]
                if genre_hits > 0:
                    reasons.append("Matches your selected genre")
                if mood_hits > 0:
                    reasons.append("Matches your selected mood")

                return RecommendationItem(
                    rank=1,
                    game_id=f"steam_{appid}",
                    title=title,
                    price=PriceInfo(amount=0.0 if is_free else price, currency="USD", is_on_sale=False),
                    match_score=max(0.1, min(score, 0.99)),
                    reasons=reasons,
                    sources=RecommendationSources(
                        steam_store_url=f"https://store.steampowered.com/app/{appid}",
                        youtube_video_url=f"https://www.youtube.com/results?search_query={title.replace(' ', '+')}+gameplay",
                        review_summary=ReviewSummaryInfo(
                            steam=SteamReviewInfo(
                                label="Very Positive" if positive_rate >= 0.8 else "Mostly Positive",
                                sample_size=total_reviews,
                            ),
                            reddit=RedditReviewInfo(
                                sentiment_score=round(0.5 + (positive_rate * 0.45), 2),
                                highlights=["offline fallback", "stable contract"],
                            ),
                        ),
                    ),
                )

            if strict_match:
                scored_strict.append((strict_score, make_item(strict_score, "strict")))
            if medium_match:
                scored_medium.append((medium_score, make_item(medium_score, "medium")))
            scored_broad.append((broad_score, make_item(broad_score, "broad")))

        scored_strict.sort(key=lambda x: x[0], reverse=True)
        scored_medium.sort(key=lambda x: x[0], reverse=True)
        scored_broad.sort(key=lambda x: x[0], reverse=True)

        strict_items = [item for _, item in scored_strict[: max(top_n * 4, top_n)]]
        medium_items = [item for _, item in scored_medium[: max(top_n * 4, top_n)]]
        broad_items = [item for _, item in scored_broad[: max(top_n * 4, top_n)]]

        selected = self._fill_tiered_items(
            top_n=top_n,
            strict_items=strict_items,
            medium_items=medium_items,
            broad_items=broad_items,
            relevance_mode=relevance_mode,
        )
        return selected[: max(top_n, 1)]

    def _build_recommendations_from_live_data(
        self,
        top_n: int,
        discord_user_id: str | None,
        genres: list[str],
        moods: list[str],
        max_price: float | None,
        relevance_mode: str,
    ) -> list[RecommendationItem]:
        try:
            candidates = steam_realtime_service.fetch_trending_games()
        except Exception:
            return []

        wanted_genres = [_normalize_label(g) for g in genres if g.strip()]
        wanted_moods = _expand_mood_tokens(moods)

        scored_strict: list[tuple[float, dict[str, object]]] = []
        scored_medium: list[tuple[float, dict[str, object]]] = []
        scored_broad: list[tuple[float, dict[str, object]]] = []
        for game in candidates:
            all_tags = _build_normalized_tags(game.get("tags", []))
            tags = _filter_gameplay_tags(all_tags)
            if max_price is not None:
                price = to_float(game.get("price", 0.0), default=0.0)
                is_free = bool(game.get("is_free", False))
                if not is_free and price > max_price:
                    continue

            genre_hits = _count_matches(wanted_genres, tags)
            mood_hits = _count_matches(wanted_moods, all_tags)
            popularity = max(0.0, min(float(game.get("positive", 0) or 0) / 50000.0, 1.0))

            if wanted_genres and genre_hits == 0:
                continue

            if (wanted_genres or wanted_moods) and (genre_hits + mood_hits == 0):
                # Never recommend fully unrelated games when filters are provided.
                continue

            # Tiered relevance matching for fill strategy.
            strict_match = True
            medium_match = True
            if wanted_genres and wanted_moods:
                strict_match = genre_hits > 0 and mood_hits > 0
                medium_match = genre_hits > 0
            elif wanted_genres:
                strict_match = genre_hits > 0
                medium_match = strict_match
            elif wanted_moods:
                strict_match = mood_hits > 0
                medium_match = strict_match

            # In strict mode, matching dominates ranking and popularity is a tiebreaker.
            score = (genre_hits * 0.75) + (mood_hits * 0.20) + (popularity * 0.05)
            if score <= 0:
                continue

            if strict_match:
                scored_strict.append((score, game))
            if medium_match:
                medium_score = (genre_hits * 0.70) + (mood_hits * 0.20) + (popularity * 0.10)
                scored_medium.append((medium_score, game))

            broad_score = (genre_hits * 0.60) + (mood_hits * 0.15) + (popularity * 0.25)
            scored_broad.append((broad_score, game))

        scored_strict.sort(key=lambda x: x[0], reverse=True)
        scored_medium.sort(key=lambda x: x[0], reverse=True)
        scored_broad.sort(key=lambda x: x[0], reverse=True)

        if not scored_broad and not scored_medium and not scored_strict:
            return []

        strict_items: list[RecommendationItem] = []
        medium_items: list[RecommendationItem] = []
        broad_items: list[RecommendationItem] = []

        def build_item(score: float, game: dict[str, object], tier: str) -> RecommendationItem:
            appid = str(game.get("appid"))
            title = str(game.get("name") or f"Steam Game {appid}")
            price = to_float(game.get("price", 0.0), default=0.0)
            is_free = bool(game.get("is_free", False))
            positive = to_int(game.get("positive", 0), default=0)
            negative = to_int(game.get("negative", 0), default=0)
            total_reviews = max(positive + negative, 1)
            positive_rate = positive / total_reviews

            all_tags = _build_normalized_tags(game.get("tags", []))
            tags = _filter_gameplay_tags(all_tags)
            genre_hits = _count_matches(wanted_genres, tags)
            mood_hits = _count_matches(wanted_moods, all_tags)

            reasons = [f"Relevance tier: {tier}", "Trending on Steam right now"]
            if genre_hits > 0:
                reasons.append("Matches your selected genre")
            if mood_hits > 0:
                reasons.append("Matches your selected mood")

            return RecommendationItem(
                rank=1,
                game_id=f"steam_{appid}",
                title=title,
                price=PriceInfo(amount=0.0 if is_free else price, currency="USD", is_on_sale=False),
                match_score=max(0.1, min(score, 0.99)),
                reasons=reasons,
                sources=RecommendationSources(
                    steam_store_url=f"https://store.steampowered.com/app/{appid}",
                    youtube_video_url=f"https://www.youtube.com/results?search_query={title.replace(' ', '+')}+gameplay",
                    review_summary=ReviewSummaryInfo(
                        steam=SteamReviewInfo(
                            label="Very Positive" if positive_rate >= 0.8 else "Mostly Positive",
                            sample_size=total_reviews,
                        ),
                        reddit=RedditReviewInfo(
                            sentiment_score=round(0.5 + (positive_rate * 0.45), 2),
                            highlights=["live steam trend", "active player interest"],
                        ),
                    ),
                ),
            )

        for score, game in scored_strict[: max(top_n * 4, top_n)]:
            strict_items.append(build_item(score, game, "strict"))
        for score, game in scored_medium[: max(top_n * 4, top_n)]:
            medium_items.append(build_item(score, game, "medium"))
        for score, game in scored_broad[: max(top_n * 4, top_n)]:
            broad_items.append(build_item(score, game, "broad"))

        selected = self._fill_tiered_items(
            top_n=top_n,
            strict_items=strict_items,
            medium_items=medium_items,
            broad_items=broad_items,
            relevance_mode=relevance_mode,
        )
        selected = self._shuffle_within_top_pool(selected, pool_size=10)
        return self._apply_freshness_filter(discord_user_id=discord_user_id, items=selected, top_n=top_n)

    def _fill_tiered_items(
        self,
        top_n: int,
        strict_items: list[RecommendationItem],
        medium_items: list[RecommendationItem],
        broad_items: list[RecommendationItem],
        relevance_mode: str,
    ) -> list[RecommendationItem]:
        selection_cap = max(top_n, 10)

        if relevance_mode == "broad":
            tier_order = [broad_items, medium_items, strict_items]
        elif relevance_mode == "medium":
            tier_order = [medium_items, strict_items, broad_items]
        else:
            tier_order = [strict_items, medium_items, broad_items]

        selected: list[RecommendationItem] = []
        selected_ids: set[str] = set()

        for tier in tier_order:
            for item in tier:
                if item.game_id in selected_ids:
                    continue
                selected.append(item)
                selected_ids.add(item.game_id)
                if len(selected) >= selection_cap:
                    break
            if len(selected) >= selection_cap:
                break

        for idx, item in enumerate(selected, start=1):
            item.rank = idx
        return selected

    def _shuffle_within_top_pool(self, items: list[RecommendationItem], pool_size: int = 10) -> list[RecommendationItem]:
        if len(items) <= 1:
            return items

        head_count = max(1, min(pool_size, len(items)))
        head = items[:head_count]
        tail = items[head_count:]
        random.shuffle(head)
        return [*head, *tail]

    def _load_steamdb_signals(self, limit: int = 5000) -> dict[int, dict[str, object]]:
        if SessionLocal.kw.get("bind") is None:
            return {}

        try:
            with SessionLocal() as db:
                rows = db.execute(
                    text(
                        """
                        WITH latest AS (
                            SELECT MAX(snapshot_at) AS snapshot_at
                            FROM steamdb_chart_snapshots
                        ),
                        s AS (
                            SELECT
                                app_id,
                                chart_type,
                                rank,
                                COALESCE(players_current, 0) AS players_current
                            FROM steamdb_chart_snapshots
                            WHERE snapshot_at = (SELECT snapshot_at FROM latest)
                              AND chart_type IN ('trending_games', 'hot_releases', 'popular_releases')
                        )
                        SELECT
                            app_id,
                            MIN(rank) AS best_rank,
                            MAX(players_current) AS max_players,
                            MAX(CASE WHEN chart_type = 'trending_games' THEN 1 ELSE 0 END) AS is_trending,
                            MAX(CASE WHEN chart_type = 'hot_releases' THEN 1 ELSE 0 END) AS is_hot_release,
                            MAX(CASE WHEN chart_type = 'popular_releases' THEN 1 ELSE 0 END) AS is_popular_release
                        FROM s
                        GROUP BY app_id
                        ORDER BY MIN(rank) ASC
                        LIMIT :limit
                        """
                    ),
                    {"limit": max(100, min(limit, 20000))},
                ).mappings().all()
        except Exception:
            return {}

        if not rows:
            return {}

        signals: dict[int, dict[str, object]] = {}
        max_players_overall = max((to_float(r.get("max_players"), default=0.0) for r in rows), default=0.0)

        for row in rows:
            app_id = to_int(row.get("app_id"), default=0)
            if app_id <= 0:
                continue

            best_rank = max(1, to_int(row.get("best_rank"), default=9999))
            rank_component = 1.0 / best_rank

            players = to_float(row.get("max_players"), default=0.0)
            players_component = (players / max_players_overall) if max_players_overall > 0 else 0.0

            hot_bonus = 0.0
            if bool(row.get("is_trending")):
                hot_bonus += 0.35
            if bool(row.get("is_hot_release")):
                hot_bonus += 0.35
            if bool(row.get("is_popular_release")):
                hot_bonus += 0.30

            boost = max(0.0, min((rank_component * 0.50) + (players_component * 0.30) + (hot_bonus * 0.20), 1.0))

            signals[app_id] = {
                "boost": boost,
                "is_trending": bool(row.get("is_trending")),
                "is_hot_release": bool(row.get("is_hot_release")),
                "is_popular_release": bool(row.get("is_popular_release")),
            }

        return signals

    def _apply_freshness_filter(
        self,
        discord_user_id: str | None,
        items: list[RecommendationItem],
        top_n: int,
    ) -> list[RecommendationItem]:
        if not items:
            return []

        if not discord_user_id:
            selected = items[:top_n]
        else:
            recent_ids = self._recent_recommendations_by_user.get(discord_user_id, [])
            recent_set = set(recent_ids)

            fresh = [item for item in items if item.game_id not in recent_set]
            seen = [item for item in items if item.game_id in recent_set]
            selected = (fresh + seen)[:top_n]

        for idx, item in enumerate(selected, start=1):
            item.rank = idx

        if discord_user_id:
            history = self._recent_recommendations_by_user.get(discord_user_id, [])
            history.extend(item.game_id for item in selected)
            self._recent_recommendations_by_user[discord_user_id] = history[-30:]

        return selected

    def save_recommendation_snapshot(
        self,
        request_id: str,
        recommendations: list[RecommendationItem],
        base_request_id: str | None = None,
    ) -> None:
        payload = [item.model_dump(mode="json") for item in recommendations]
        with SessionLocal() as db:
            row = RecommendationSnapshot(
                request_id=request_id,
                base_request_id=base_request_id,
                payload=payload,
                created_at=utc_now(),
            )
            db.add(row)
            db.commit()

    def get_recommendation_snapshot(self, request_id: str) -> list[RecommendationItem] | None:
        with SessionLocal() as db:
            row = db.execute(
                select(RecommendationSnapshot).where(RecommendationSnapshot.request_id == request_id)
            ).scalar_one_or_none()
            if row is None:
                return None
            return [RecommendationItem.model_validate(item) for item in row.payload]

    def record_feedback(self, payload: FeedbackRequest, idempotency_key: str | None) -> bool:
        with SessionLocal() as db:
            if idempotency_key:
                existing = db.execute(
                    select(FeedbackEvent).where(FeedbackEvent.idempotency_key == idempotency_key)
                ).scalar_one_or_none()
                if existing is not None:
                    return False

            db.add(
                FeedbackEvent(
                    discord_user_id=payload.discord_user_id,
                    game_id=payload.game_id,
                    feedback_type=payload.feedback_type,
                    context=payload.context,
                    idempotency_key=idempotency_key,
                    created_at=utc_now(),
                )
            )
            db.commit()
            return True

    def list_recommendation_tags(self, query: str = "", limit: int = 25) -> list[str]:
        if SessionLocal.kw.get("bind") is None:
            return DEFAULT_DISCOVERY_TAGS[: max(1, min(limit, 100))]

        safe_limit = max(1, min(limit, 100))
        q = query.strip().lower()

        try:
            with SessionLocal() as db:
                rows = db.execute(
                    text(
                        """
                        SELECT tag, SUM(weight) AS score
                        FROM (
                            SELECT lower(trim(unnest(COALESCE(g.genres, '{}')))) AS tag, 3 AS weight
                            FROM games g
                            UNION ALL
                            SELECT lower(trim(unnest(COALESCE(g.normalized_gameplay_tags, '{}')))) AS tag, 2 AS weight
                            FROM games g
                            UNION ALL
                            SELECT lower(trim(unnest(COALESCE(g.tags, '{}')))) AS tag, 1 AS weight
                            FROM games g
                        ) t
                        WHERE tag IS NOT NULL
                          AND tag <> ''
                          AND (:query = '' OR lower(tag) LIKE '%' || :query || '%')
                        GROUP BY tag
                        ORDER BY score DESC, tag ASC
                        LIMIT :fetch_limit
                        """
                    ),
                    {"query": q, "fetch_limit": max(100, safe_limit * 4)},
                ).mappings().all()
        except Exception:
            rows = []

        ranked = [str(row["tag"]) for row in rows if row.get("tag")]
        filtered = _filter_gameplay_tags(ranked)

        if q:
            filtered = [tag for tag in filtered if q in tag]

        merged: list[str] = []
        seen: set[str] = set()
        for tag in [*filtered, *DEFAULT_DISCOVERY_TAGS]:
            token = _normalize_label(tag)
            if not token or token in seen:
                continue
            if q and q not in token:
                continue
            seen.add(token)
            merged.append(token)
            if len(merged) >= safe_limit:
                break

        if not merged and q:
            return [q]
        return merged[:safe_limit]

    def search_games(self, query: str, limit: int) -> list[GameSearchItem]:
        q = query.lower().strip()
        matches = [g for g in self.games if q in g.title.lower()]
        return [
            GameSearchItem(game_id=game.game_id, title=game.title, genres=game.genres)
            for game in matches[:limit]
        ]

    def get_game(self, game_id: str) -> GameDetailResponse | None:
        for game in self.games:
            if game.game_id == game_id:
                return game
        return None


store = PersistentStore()
