from __future__ import annotations

from uuid import uuid4
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import require_bot_auth
from app.schemas.contracts import (
    RecommendationExplainResponse,
    RecommendationGenerateRequest,
    RecommendationRefineRequest,
    RecommendationResponse,
)
from app.services.store import store, utc_now

router = APIRouter(dependencies=[Depends(require_bot_auth)])


@router.post("/generate", response_model=RecommendationResponse)
def generate_recommendations(payload: RecommendationGenerateRequest) -> RecommendationResponse:
    request_id = f"req_{uuid4().hex[:12]}"
    max_price = payload.session_intent.budget.max_price if payload.session_intent.budget else None
    recommendations = store.build_recommendations(
        payload.options.top_n,
        payload.discord_user_id,
        payload.session_intent.genre,
        payload.session_intent.mood,
        max_price,
        payload.options.relevance_mode,
    )
    if not recommendations:
        raise HTTPException(status_code=404, detail="No recommendations found")
    store.save_recommendation_snapshot(request_id=request_id, recommendations=recommendations)
    return RecommendationResponse(
        request_id=request_id,
        generated_at=utc_now(),
        recommendations=recommendations,
    )


@router.post("/refine", response_model=RecommendationResponse)
def refine_recommendations(payload: RecommendationRefineRequest) -> RecommendationResponse:
    base = store.get_recommendation_snapshot(payload.base_request_id)
    if base is None:
        raise HTTPException(status_code=404, detail="base_request_id not found")

    request_id = f"req_{uuid4().hex[:12]}"
    raw_exclude_ids: Any = payload.adjustments.get("exclude_game_ids", [])
    exclude_ids = set(raw_exclude_ids) if isinstance(raw_exclude_ids, list) else set()
    refined = [item for item in base if item.game_id not in exclude_ids]

    if not refined:
        refined = store.build_recommendations(top_n=3, discord_user_id=payload.discord_user_id)

    store.save_recommendation_snapshot(
        request_id=request_id,
        recommendations=refined,
        base_request_id=payload.base_request_id,
    )
    return RecommendationResponse(
        request_id=request_id,
        base_request_id=payload.base_request_id,
        generated_at=utc_now(),
        recommendations=refined,
    )


@router.get("/explain", response_model=RecommendationExplainResponse)
def explain_recommendation(discord_user_id: str = Query(), game_id: str = Query()) -> RecommendationExplainResponse:
    return RecommendationExplainResponse(
        discord_user_id=discord_user_id,
        game_id=game_id,
        explanation={
            "score_breakdown": {
                "profile_match": 0.42,
                "session_intent_match": 0.30,
                "community_signal": 0.15,
                "novelty": 0.04,
                "penalty": 0.00,
            },
            "human_reasons": [
                "Ban choi nhieu game cung the loai trong 90 ngay",
                "Thoi luong session hien tai hop voi game nay",
            ],
        },
    )


@router.get("/tag-options")
def tag_options(query: str = Query(default=""), limit: int = Query(default=25, ge=1, le=100)) -> dict[str, list[str]]:
    return {"items": store.list_recommendation_tags(query=query, limit=limit)}
