from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.security import require_bot_auth
from app.services.store import store

router = APIRouter(dependencies=[Depends(require_bot_auth)])


@router.get("")
def semantic_search(query: str = Query(min_length=1), limit: int = Query(default=5, ge=1, le=20)) -> dict[str, object]:
    matches = []
    q = query.lower().strip()
    for game in store.games:
        haystack = f"{game.title} {' '.join(game.genres)} {game.description}".lower()
        if q in haystack:
            matches.append(
                {
                    "game_id": game.game_id,
                    "title": game.title,
                    "genres": game.genres,
                }
            )

    return {"query": query, "results": matches[:limit]}
