from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.config import settings


def require_bot_auth(authorization: str | None = Header(default=None, alias="Authorization")) -> None:
	if not authorization:
		raise HTTPException(status_code=401, detail="Missing Authorization header")

	scheme, _, token = authorization.partition(" ")
	if scheme.lower() != "bearer" or not token:
		raise HTTPException(status_code=401, detail="Invalid Authorization scheme")

	if token != settings.bot_service_token:
		raise HTTPException(status_code=403, detail="Invalid bot token")
