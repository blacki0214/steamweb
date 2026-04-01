from __future__ import annotations

import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Indie Game API"
    bot_service_token: str = os.getenv("BOT_SERVICE_TOKEN", "dev-bot-token")
    public_api_base_url: str = os.getenv("PUBLIC_API_BASE_URL", "http://localhost:8001")
    steam_openid_endpoint: str = os.getenv(
        "STEAM_OPENID_ENDPOINT",
        "https://steamcommunity.com/openid/login",
    )
    steam_verify_openid: bool = os.getenv("STEAM_VERIFY_OPENID", "false").lower() == "true"
    steam_openid_claimed_id_prefix: str = os.getenv(
        "STEAM_OPENID_CLAIMED_ID_PREFIX",
        "https://steamcommunity.com/openid/id/",
    )
    steam_web_api_key: str = os.getenv("STEAM_WEB_API_KEY", "")


settings = Settings()
