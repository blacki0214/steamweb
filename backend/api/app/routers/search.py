from fastapi import APIRouter

router = APIRouter()


@router.get("")
def semantic_search(query: str) -> dict[str, object]:
    return {"query": query, "results": []}
