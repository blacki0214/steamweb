from fastapi import APIRouter

router = APIRouter()


@router.get("/{game_id}")
def review_summary(game_id: str) -> dict[str, object]:
    return {"game_id": game_id, "summary": ""}
