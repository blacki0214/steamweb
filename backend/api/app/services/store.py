from __future__ import annotations

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

        default_reasons = [
            "Phu hop voi lich su the loai ban da choi",
            "Phu hop voi intent session hien tai",
            "Sentiment cong dong dang tich cuc",
        ]

        wanted_genres = [g.strip().lower() for g in (genres or []) if g.strip()]
        wanted_moods = [m.strip().lower() for m in (moods or []) if m.strip()]
        fallback_mood_tag_map: dict[str, list[str]] = {
            "chill": ["cozy", "simulation", "casual"],
            "intense": ["action", "roguelike", "metroidvania"],
            "story-rich": ["rpg", "adventure"],
            "co-op": ["multiplayer", "co-op"],
            "competitive": ["pvp", "competitive", "action"],
            "relaxing": ["cozy", "casual", "simulation"],
            "dark": ["horror", "dark", "metroidvania"],
            "creative": ["sandbox", "building", "simulation"],
        }
        mood_tags = [tag for mood in wanted_moods for tag in fallback_mood_tag_map.get(mood, [mood])]

        strict_items: list[RecommendationItem] = []
        medium_items: list[RecommendationItem] = []
        broad_items: list[RecommendationItem] = []

        for game in self.games:
            if max_price is not None and game.price.amount > max_price:
                continue

            game_tags = [g.lower() for g in game.genres]
            genre_hit = any(any(w in tag or tag in w for tag in game_tags) for w in wanted_genres)
            mood_hit = any(any(m in tag or tag in m for tag in game_tags) for m in mood_tags)

            has_filters = bool(wanted_genres or wanted_moods)
            strict_match = True
            medium_match = True
            if has_filters:
                if wanted_genres and wanted_moods:
                    strict_match = genre_hit and mood_hit
                    medium_match = genre_hit or mood_hit
                elif wanted_genres:
                    strict_match = genre_hit
                    medium_match = genre_hit
                elif wanted_moods:
                    strict_match = mood_hit
                    medium_match = mood_hit

                # Keep fallback relevant: if user provided filters, skip total misses.
                if not (genre_hit or mood_hit):
                    continue

            item = RecommendationItem(
                rank=1,
                game_id=game.game_id,
                title=game.title,
                price=game.price,
                match_score=0.6,
                reasons=default_reasons,
                sources=RecommendationSources(
                    steam_store_url=game.steam_store_url,
                    youtube_video_url=game.youtube_video_url,
                    review_summary=ReviewSummaryInfo(
                        steam=SteamReviewInfo(label="Very Positive", sample_size=1200),
                        reddit=RedditReviewInfo(
                            sentiment_score=0.74,
                            highlights=["combat muot", "replay value cao"],
                        ),
                    ),
                ),
            )

            if strict_match:
                tagged = item.model_copy(deep=True)
                tagged.reasons = ["Relevance tier: strict", *tagged.reasons]
                strict_items.append(tagged)
            if medium_match:
                tagged = item.model_copy(deep=True)
                tagged.reasons = ["Relevance tier: medium", *tagged.reasons]
                medium_items.append(tagged)

            tagged = item.model_copy(deep=True)
            tagged.reasons = ["Relevance tier: broad", *tagged.reasons]
            broad_items.append(tagged)

        selected = self._fill_tiered_items(
            top_n=top_n,
            strict_items=strict_items,
            medium_items=medium_items,
            broad_items=broad_items,
            relevance_mode=relevance_mode,
        )
        return self._apply_freshness_filter(discord_user_id=discord_user_id, items=selected, top_n=top_n)

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

        mood_tag_map: dict[str, list[str]] = {
            "chill": ["casual", "cozy", "relaxing", "simulation"],
            "intense": ["action", "souls-like", "difficult", "shooter"],
            "story-rich": ["story rich", "narrative", "adventure", "rpg"],
            "co-op": ["co-op", "online co-op", "multiplayer"],
            "competitive": ["competitive", "pvp", "esports", "multiplayer"],
            "relaxing": ["relaxing", "cozy", "casual"],
            "dark": ["horror", "dark fantasy", "psychological horror"],
            "creative": ["sandbox", "building", "crafting", "simulation"],
        }

        try:
            with SessionLocal() as db:
                rows = db.execute(
                    text(
                        """
                        SELECT
                            g.id,
                            g.name,
                            COALESCE(g.short_description, g.description, '') AS description,
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
                    {"limit": max(top_n * 20, 100)},
                ).mappings().all()
        except Exception:
            return []

        if not rows:
            return []

        wanted_genres = [g.strip().lower() for g in genres if g.strip()]
        wanted_moods = [m.strip().lower() for m in moods if m.strip()]
        mood_tags = [tag for mood in wanted_moods for tag in mood_tag_map.get(mood, [mood])]

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

            raw_genres = row.get("genres")
            raw_tags = row.get("tags")
            tags: list[str] = []
            if isinstance(raw_genres, list):
                tags.extend(str(t).lower() for t in raw_genres)
            if isinstance(raw_tags, list):
                tags.extend(str(t).lower() for t in raw_tags)

            genre_hits = sum(1 for g in wanted_genres if any(g in t or t in g for t in tags))
            mood_hits = sum(1 for m in mood_tags if any(m in t or t in m for t in tags))

            if (wanted_genres or wanted_moods) and (genre_hits + mood_hits == 0):
                continue

            total_reviews = to_int(row.get("total_reviews"), default=0)
            positive_reviews = to_int(row.get("positive_reviews"), default=0)
            popularity = max(0.0, min(float(positive_reviews) / 50000.0, 1.0))

            strict_match = True
            medium_match = True
            if wanted_genres and wanted_moods:
                strict_match = genre_hits > 0 and mood_hits > 0
                medium_match = genre_hits > 0 or mood_hits > 0
            elif wanted_genres:
                strict_match = genre_hits > 0
                medium_match = strict_match
            elif wanted_moods:
                strict_match = mood_hits > 0
                medium_match = strict_match

            strict_score = (genre_hits * 0.6) + (mood_hits * 0.35) + (popularity * 0.05)
            medium_score = (genre_hits * 0.55) + (mood_hits * 0.35) + (popularity * 0.10)
            broad_score = (genre_hits * 0.45) + (mood_hits * 0.30) + (popularity * 0.25)

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
        return self._apply_freshness_filter(discord_user_id=discord_user_id, items=selected, top_n=top_n)

    def _build_recommendations_from_live_data(
        self,
        top_n: int,
        discord_user_id: str | None,
        genres: list[str],
        moods: list[str],
        max_price: float | None,
        relevance_mode: str,
    ) -> list[RecommendationItem]:
        mood_tag_map: dict[str, list[str]] = {
            "chill": ["casual", "cozy", "relaxing", "simulation"],
            "intense": ["action", "souls-like", "difficult", "shooter"],
            "story-rich": ["story rich", "narrative", "adventure", "rpg"],
            "co-op": ["co-op", "online co-op", "multiplayer"],
            "competitive": ["competitive", "pvp", "esports", "multiplayer"],
            "relaxing": ["relaxing", "cozy", "casual"],
            "dark": ["horror", "dark fantasy", "psychological horror"],
            "creative": ["sandbox", "building", "crafting", "simulation"],
        }

        try:
            candidates = steam_realtime_service.fetch_trending_games()
        except Exception:
            return []

        wanted_genres = [g.strip().lower() for g in genres if g.strip()]
        wanted_moods = [m.strip().lower() for m in moods if m.strip()]
        mood_tags = [tag for mood in wanted_moods for tag in mood_tag_map.get(mood, [mood])]

        scored_strict: list[tuple[float, dict[str, object]]] = []
        scored_medium: list[tuple[float, dict[str, object]]] = []
        scored_broad: list[tuple[float, dict[str, object]]] = []
        for game in candidates:
            tags = [str(tag).lower() for tag in game.get("tags", [])]
            if max_price is not None:
                price = to_float(game.get("price", 0.0), default=0.0)
                is_free = bool(game.get("is_free", False))
                if not is_free and price > max_price:
                    continue

            genre_hits = sum(1 for g in wanted_genres if any(g in t or t in g for t in tags))
            mood_hits = sum(1 for m in mood_tags if any(m in t or t in m for t in tags))
            popularity = max(0.0, min(float(game.get("positive", 0) or 0) / 50000.0, 1.0))

            if (wanted_genres or wanted_moods) and (genre_hits + mood_hits == 0):
                # Never recommend fully unrelated games when filters are provided.
                continue

            # Tiered relevance matching for fill strategy.
            strict_match = True
            medium_match = True
            if wanted_genres and wanted_moods:
                strict_match = genre_hits > 0 and mood_hits > 0
                medium_match = genre_hits > 0 or mood_hits > 0
            elif wanted_genres:
                strict_match = genre_hits > 0
                medium_match = strict_match
            elif wanted_moods:
                strict_match = mood_hits > 0
                medium_match = strict_match

            # In strict mode, matching dominates ranking and popularity is a tiebreaker.
            score = (genre_hits * 0.6) + (mood_hits * 0.35) + (popularity * 0.05)
            if score <= 0:
                continue

            if strict_match:
                scored_strict.append((score, game))
            if medium_match:
                medium_score = (genre_hits * 0.55) + (mood_hits * 0.35) + (popularity * 0.10)
                scored_medium.append((medium_score, game))

            broad_score = (genre_hits * 0.45) + (mood_hits * 0.3) + (popularity * 0.25)
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

            tags_raw = game.get("tags", [])
            tags = [str(tag).lower() for tag in tags_raw] if isinstance(tags_raw, list) else []
            genre_hits = sum(1 for g in wanted_genres if any(g in t or t in g for t in tags))
            mood_hits = sum(1 for m in mood_tags if any(m in t or t in m for t in tags))

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
        return self._apply_freshness_filter(discord_user_id=discord_user_id, items=selected, top_n=top_n)

    def _fill_tiered_items(
        self,
        top_n: int,
        strict_items: list[RecommendationItem],
        medium_items: list[RecommendationItem],
        broad_items: list[RecommendationItem],
        relevance_mode: str,
    ) -> list[RecommendationItem]:
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
                if len(selected) >= top_n:
                    break
            if len(selected) >= top_n:
                break

        for idx, item in enumerate(selected, start=1):
            item.rank = idx
        return selected

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
