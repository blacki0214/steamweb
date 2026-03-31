from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_games() -> list[dict[str, str]]:
    return []
