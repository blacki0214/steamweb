from __future__ import annotations

import html
from urllib.parse import urlencode
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import settings
from app.core.security import require_bot_auth
from app.schemas.contracts import ConnectLinkRequest, ConnectLinkResponse
from app.services.store import store, utc_now

router = APIRouter()


def _fetch_steam_profile(steam_id: str) -> dict[str, str] | None:
    """Fetch basic Steam profile data for friendly callback rendering."""
    if not settings.steam_web_api_key:
        return None

    try:
        resp = httpx.get(
            "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
            params={"key": settings.steam_web_api_key, "steamids": steam_id},
            timeout=15,
        )
        resp.raise_for_status()
        players = resp.json().get("response", {}).get("players", [])
        if not players:
            return None
        player = players[0]
        return {
            "persona_name": str(player.get("personaname", "Steam User")),
            "profile_url": str(player.get("profileurl", "")),
            "avatar_url": str(player.get("avatarfull", "")),
        }
    except Exception:
        return None


def _fetch_owned_games_summary(steam_id: str) -> dict[str, object] | None:
    """Fetch owned games and aggregate playtime stats."""
    if not settings.steam_web_api_key:
        return None

    try:
        resp = httpx.get(
            "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
            params={
                "key": settings.steam_web_api_key,
                "steamid": steam_id,
                "include_appinfo": 1,
                "include_played_free_games": 1,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json().get("response", {})
        games = data.get("games", [])

        total_games = int(data.get("game_count", len(games)))
        total_minutes = sum(int(g.get("playtime_forever", 0) or 0) for g in games)

        top_games = sorted(
            games,
            key=lambda g: int(g.get("playtime_forever", 0) or 0),
            reverse=True,
        )[:5]

        return {
            "total_games": total_games,
            "total_playtime_hours": round(total_minutes / 60, 1),
            "top_games": [
                {
                    "name": str(g.get("name", f"App {g.get('appid', '')}")),
                    "hours": round((int(g.get("playtime_forever", 0) or 0)) / 60, 1),
                }
                for g in top_games
            ],
        }
    except Exception:
        return None


def _build_success_html(
    steam_id: str,
    redirect_uri: str,
    profile: dict[str, str] | None,
    game_summary: dict[str, object] | None,
) -> str:
    """Build a user-friendly Steam linking success page."""
    safe_steam_id = html.escape(steam_id)
    safe_redirect_uri = html.escape(redirect_uri)

    persona_name = html.escape((profile or {}).get("persona_name", "Steam User"))
    profile_url = html.escape((profile or {}).get("profile_url", ""))
    avatar_url = html.escape((profile or {}).get("avatar_url", ""))

    total_games = "N/A"
    total_playtime_hours = "N/A"
    top_games_html = "<li>Could not load game stats yet.</li>"

    if game_summary:
        total_games = str(game_summary.get("total_games", "N/A"))
        total_playtime_hours = str(game_summary.get("total_playtime_hours", "N/A"))
        top_games = game_summary.get("top_games", [])
        if isinstance(top_games, list) and top_games:
            top_games_html = "".join(
                f"<li>{html.escape(str(g.get('name', 'Unknown')))} - {g.get('hours', 0)}h</li>"
                for g in top_games
            )

    profile_block = ""
    if profile:
        avatar_img = (
            f'<img src="{avatar_url}" alt="avatar" style="width:64px;height:64px;border-radius:50%;object-fit:cover;"/>'
            if avatar_url
            else ""
        )
        name_link = (
            f'<a href="{profile_url}" target="_blank" rel="noopener noreferrer">{persona_name}</a>'
            if profile_url
            else persona_name
        )
        profile_block = (
            '<div style="display:flex;align-items:center;gap:12px;margin-top:12px;">'
            f"{avatar_img}"
            f"<div><div style=\"font-weight:600;\">{name_link}</div><div style=\"color:#555;\">Steam ID: {safe_steam_id}</div></div>"
            "</div>"
        )

    continue_button = (
        f'<a href="{safe_redirect_uri}" style="display:inline-block;margin-top:16px;padding:10px 14px;background:#171a21;color:#fff;text-decoration:none;border-radius:8px;">Continue</a>'
        if redirect_uri
        else ""
    )

    identity_block = profile_block or (
        f'<p style="margin-top:12px;">Steam ID: <strong>{safe_steam_id}</strong></p>'
    )

    return (
        "<html><body style='font-family:Segoe UI,Arial,sans-serif;background:#f6f7f9;padding:28px;'>"
        "<div style='max-width:720px;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px;'>"
        "<h2 style='margin:0 0 8px 0;color:#111827;'>Steam account linked successfully</h2>"
        "<p style='margin:0;color:#4b5563;'>You can now use your Steam profile for personalized recommendations.</p>"
        f"{identity_block}"
        "<div style='margin-top:18px;padding:14px;border:1px solid #e5e7eb;border-radius:10px;background:#fafafa;'>"
        "<div style='font-weight:600;margin-bottom:8px;'>Gameplay Summary</div>"
        f"<div>Total games: <strong>{total_games}</strong></div>"
        f"<div>Total playtime: <strong>{total_playtime_hours} hours</strong></div>"
        "<div style='margin-top:8px;'>Top played games:</div>"
        f"<ul style='margin:6px 0 0 18px;padding:0;'>{top_games_html}</ul>"
        "</div>"
        f"{continue_button}"
        "</div></body></html>"
    )


@router.post("/steam/connect-link", response_model=ConnectLinkResponse)
def create_connect_link(
    payload: ConnectLinkRequest,
    _: None = Depends(require_bot_auth),
) -> ConnectLinkResponse:
    state, expires_at = store.create_state(
        discord_user_id=payload.discord_user_id,
        redirect_uri=payload.redirect_uri,
    )
    connect_url = f"{settings.public_api_base_url.rstrip('/')}/api/v1/auth/steam/start?state={state}"
    return ConnectLinkResponse(connect_url=connect_url, state=state, expires_at=expires_at)


@router.get("/steam/start")
def steam_start(state: str) -> RedirectResponse:
    oauth_state = store.get_oauth_state(state)
    if oauth_state is None:
        raise HTTPException(status_code=404, detail="Invalid state")

    callback_url = f"{settings.public_api_base_url.rstrip('/')}/api/v1/auth/steam/callback"
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": f"{callback_url}?state={state}",
        "openid.realm": settings.public_api_base_url.rstrip("/"),
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return RedirectResponse(url=f"{settings.steam_openid_endpoint}?{urlencode(params)}")


def _verify_steam_openid(query_params: dict[str, str]) -> bool:
    verification_payload = dict(query_params)
    verification_payload["openid.mode"] = "check_authentication"
    response = httpx.post(settings.steam_openid_endpoint, data=verification_payload, timeout=15)
    return "is_valid:true" in response.text


@router.get("/steam/callback")
def steam_callback(
    request: Request,
    state: str,
    openid_claimed_id: str = Query(alias="openid.claimed_id"),
) -> HTMLResponse:
    oauth_state = store.get_oauth_state(state)
    if oauth_state is None:
        raise HTTPException(status_code=404, detail="Invalid or expired state")

    expires_at = oauth_state.get("expires_at")
    if isinstance(expires_at, datetime) and expires_at < utc_now():
        raise HTTPException(status_code=404, detail="Invalid or expired state")

    if settings.steam_verify_openid:
        all_params = {k: v for k, v in request.query_params.multi_items()}
        if not _verify_steam_openid(all_params):
            raise HTTPException(status_code=400, detail="Steam OpenID verification failed")

    if not openid_claimed_id.startswith(settings.steam_openid_claimed_id_prefix):
        raise HTTPException(status_code=400, detail="Invalid Steam claimed ID format")

    # Steam claimed ID typically ends with the steam64 id.
    steam_id = openid_claimed_id.rsplit("/", maxsplit=1)[-1]
    if not steam_id.isdigit():
        raise HTTPException(status_code=400, detail="Invalid Steam ID")

    connection = store.complete_oauth(state=state, steam_id=steam_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Invalid or expired state")

    redirect_uri = str(oauth_state.get("redirect_uri") or "")
    discord_user_id = str(oauth_state.get("discord_user_id") or "")
    profile = _fetch_steam_profile(steam_id)
    game_summary = _fetch_owned_games_summary(steam_id)

    if discord_user_id:
        store.upsert_steam_stats(
            discord_user_id=discord_user_id,
            steam_id=steam_id,
            profile=profile,
            game_summary=game_summary,
        )

    return HTMLResponse(content=_build_success_html(steam_id, redirect_uri, profile, game_summary))