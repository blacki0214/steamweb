from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from app.core.security import require_bot_auth
from app.schemas.contracts import FeedbackRequest, FeedbackResponse
from app.services.store import store

router = APIRouter(dependencies=[Depends(require_bot_auth)])


@router.post("", response_model=FeedbackResponse)
def create_feedback(payload: FeedbackRequest, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> FeedbackResponse:
    recorded = store.record_feedback(payload=payload, idempotency_key=idempotency_key)
    if not recorded:
        return FeedbackResponse(success=True, applied=True, message="Feedback already recorded")

    return FeedbackResponse(success=True, applied=True, message="Feedback recorded")