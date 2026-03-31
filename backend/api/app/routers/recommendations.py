from fastapi import APIRouter

router = APIRouter()


@router.get("/{user_id}")
def recommend_for_user(user_id: str) -> dict[str, object]:
    return {"user_id": user_id, "recommendations": []}
