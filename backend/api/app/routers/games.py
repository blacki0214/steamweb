from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import require_bot_auth
from app.schemas.contracts import GameDetailResponse, GameSearchResponse
from app.services.store import store

router = APIRouter(dependencies=[Depends(require_bot_auth)])


@router.get("/search", response_model=GameSearchResponse)
def search_games(query: str = Query(min_length=1), limit: int = Query(default=5, ge=1, le=20)) -> GameSearchResponse:
    items = store.search_games(query=query, limit=limit)
    return GameSearchResponse(items=items)


@router.get("/{game_id}", response_model=GameDetailResponse)
def get_game_detail(game_id: str) -> GameDetailResponse:
    game = store.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game
