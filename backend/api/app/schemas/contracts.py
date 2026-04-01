from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ConnectLinkRequest(BaseModel):
    discord_user_id: str
    discord_guild_id: str | None = None
    redirect_uri: str


class ConnectLinkResponse(BaseModel):
    connect_url: str
    state: str
    expires_at: datetime


class SteamTopGame(BaseModel):
    name: str
    hours: float


class SteamConnectionStatus(BaseModel):
    discord_user_id: str
    is_connected: bool
    steam_id: str | None = None
    connected_at: datetime | None = None
    persona_name: str | None = None
    profile_url: str | None = None
    avatar_url: str | None = None
    total_games: int | None = None
    total_playtime_hours: float | None = None
    top_games: list[SteamTopGame] = Field(default_factory=list)
    synced_at: datetime | None = None


class GenericSuccessResponse(BaseModel):
    success: bool = True
    message: str | None = None


class UserProfile(BaseModel):
    discord_user_id: str
    steam_connected: bool = False
    top_genres: list[str] = Field(default_factory=list)
    mood_preferences: list[str] = Field(default_factory=list)
    play_style: dict[str, object] = Field(default_factory=dict)
    updated_at: datetime


class UpdateUserProfileRequest(BaseModel):
    top_genres: list[str] | None = None
    mood_preferences: list[str] | None = None
    budget_preference: str | None = None


class BudgetPreference(BaseModel):
    mode: Literal["under_price", "free", "no_limit"] = "no_limit"
    currency: str | None = None
    max_price: float | None = None


class SessionIntent(BaseModel):
    genre: list[str] = Field(default_factory=list)
    mood: list[str] = Field(default_factory=list)
    session_length_minutes: int | None = None
    budget: BudgetPreference | None = None
    multiplayer: Literal["solo", "co_op", "any"] | None = None


class RecommendationOptions(BaseModel):
    top_n: int = 5
    exclude_owned: bool = False
    exclude_already_played: bool = True
    include_video: bool = True
    include_review_summary: bool = True
    relevance_mode: Literal["strict", "medium", "broad"] = "medium"


class RecommendationGenerateRequest(BaseModel):
    discord_user_id: str
    session_intent: SessionIntent
    options: RecommendationOptions = Field(default_factory=RecommendationOptions)


class RecommendationRefineRequest(BaseModel):
    discord_user_id: str
    base_request_id: str
    adjustments: dict[str, object] = Field(default_factory=dict)


class PriceInfo(BaseModel):
    amount: float
    currency: str
    is_on_sale: bool = False


class SteamReviewInfo(BaseModel):
    label: str
    sample_size: int


class RedditReviewInfo(BaseModel):
    sentiment_score: float
    highlights: list[str] = Field(default_factory=list)


class ReviewSummaryInfo(BaseModel):
    steam: SteamReviewInfo
    reddit: RedditReviewInfo


class RecommendationSources(BaseModel):
    steam_store_url: str
    youtube_video_url: str | None = None
    review_summary: ReviewSummaryInfo | None = None


class RecommendationItem(BaseModel):
    rank: int
    game_id: str
    title: str
    price: PriceInfo
    match_score: float
    reasons: list[str] = Field(default_factory=list)
    sources: RecommendationSources


class RecommendationResponse(BaseModel):
    request_id: str
    generated_at: datetime
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    base_request_id: str | None = None


class RecommendationExplainResponse(BaseModel):
    discord_user_id: str
    game_id: str
    explanation: dict[str, object]


class FeedbackRequest(BaseModel):
    discord_user_id: str
    game_id: str
    feedback_type: Literal[
        "like",
        "dislike",
        "already_played",
        "clicked_video",
        "clicked_store",
        "wishlist_added",
    ]
    context: dict[str, object] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    success: bool = True
    applied: bool = True
    message: str = "Feedback recorded"


class GameSearchItem(BaseModel):
    game_id: str
    title: str
    genres: list[str] = Field(default_factory=list)


class GameSearchResponse(BaseModel):
    items: list[GameSearchItem] = Field(default_factory=list)


class GameDetailResponse(BaseModel):
    game_id: str
    title: str
    description: str
    genres: list[str] = Field(default_factory=list)
    price: PriceInfo
    youtube_video_url: str | None = None
    steam_store_url: str
