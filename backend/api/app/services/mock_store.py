from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.schemas.contracts import (
    GameDetailResponse,
    GameSearchItem,
    RecommendationItem,
    RecommendationSources,
    ReviewSummaryInfo,
    PriceInfo,
    RedditReviewInfo,
    SteamReviewInfo,
    UserProfile,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class MockStore:
    def __init__(self) -> None:
        self.pending_states: dict[str, dict[str, str]] = {}
        self.user_connections: dict[str, dict[str, object]] = {}
        self.user_profiles: dict[str, UserProfile] = {}
        self.feedback_events: list[dict[str, object]] = []
        self.feedback_by_idempotency_key: dict[str, dict[str, object]] = {}
        self.recommendation_snapshots: dict[str, list[RecommendationItem]] = {}

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
        ]

    def create_state(self, discord_user_id: str, redirect_uri: str) -> tuple[str, datetime]:
        state = f"st_{uuid4().hex[:18]}"
        expires_at = utc_now() + timedelta(minutes=15)
        self.pending_states[state] = {
            "discord_user_id": discord_user_id,
            "redirect_uri": redirect_uri,
        }
        return state, expires_at

    def complete_oauth(self, state: str, steam_id: str) -> dict[str, object] | None:
        payload = self.pending_states.pop(state, None)
        if not payload:
            return None

        discord_user_id = str(payload["discord_user_id"])
        connected_at = utc_now()
        self.user_connections[discord_user_id] = {
            "steam_id": steam_id,
            "connected_at": connected_at,
        }

        if discord_user_id not in self.user_profiles:
            self.user_profiles[discord_user_id] = UserProfile(
                discord_user_id=discord_user_id,
                steam_connected=True,
                top_genres=["roguelike", "metroidvania"],
                mood_preferences=["intense", "story-rich"],
                play_style={"session_minutes_preference": 60, "budget_preference": "low"},
                updated_at=utc_now(),
            )
        else:
            profile = self.user_profiles[discord_user_id]
            profile.steam_connected = True
            profile.updated_at = utc_now()

        return self.user_connections[discord_user_id]

    def get_connection(self, discord_user_id: str) -> dict[str, object] | None:
        return self.user_connections.get(discord_user_id)

    def unlink_connection(self, discord_user_id: str) -> None:
        self.user_connections.pop(discord_user_id, None)
        profile = self.user_profiles.get(discord_user_id)
        if profile:
            profile.steam_connected = False
            profile.updated_at = utc_now()

    def get_or_create_profile(self, discord_user_id: str) -> UserProfile:
        if discord_user_id not in self.user_profiles:
            self.user_profiles[discord_user_id] = UserProfile(
                discord_user_id=discord_user_id,
                steam_connected=discord_user_id in self.user_connections,
                top_genres=[],
                mood_preferences=[],
                play_style={},
                updated_at=utc_now(),
            )
        return self.user_profiles[discord_user_id]

    def build_recommendations(self, top_n: int) -> list[RecommendationItem]:
        default_reasons = [
            "Phu hop voi lich su the loai ban da choi",
            "Phu hop voi intent session hien tai",
            "Sentiment cong dong dang tich cuc",
        ]

        rows: list[RecommendationItem] = []
        for rank, game in enumerate(self.games[:top_n], start=1):
            rows.append(
                RecommendationItem(
                    rank=rank,
                    game_id=game.game_id,
                    title=game.title,
                    price=game.price,
                    match_score=max(0.5, 1 - (rank * 0.08)),
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
            )
        return rows

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


store = MockStore()
