from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_bot_auth
from app.services.store import store

router = APIRouter(dependencies=[Depends(require_bot_auth)])


@router.get("/{game_id}")
def review_summary(game_id: str) -> dict[str, object]:
    game = store.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    return {
        "game_id": game_id,
        "summary": {
            "steam": {
                "label": "Very Positive",
                "sample_size": 1200,
            },
            "reddit": {
                "sentiment_score": 0.74,
                "highlights": ["combat muot", "replay value cao"],
            },
        },
    }
