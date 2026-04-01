from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import require_bot_auth
from app.schemas.contracts import GenericSuccessResponse, SteamConnectionStatus, UpdateUserProfileRequest, UserProfile
from app.services.store import store, utc_now

router = APIRouter(dependencies=[Depends(require_bot_auth)])


@router.get("/{discord_user_id}/connections/steam", response_model=SteamConnectionStatus)
def get_steam_connection(discord_user_id: str) -> SteamConnectionStatus:
    connection = store.get_connection(discord_user_id)
    if not connection:
        return SteamConnectionStatus(discord_user_id=discord_user_id, is_connected=False)

    return SteamConnectionStatus(
        discord_user_id=discord_user_id,
        is_connected=True,
        steam_id=str(connection["steam_id"]),
        connected_at=connection["connected_at"],
        persona_name=connection.get("persona_name"),
        profile_url=connection.get("profile_url"),
        avatar_url=connection.get("avatar_url"),
        total_games=connection.get("total_games"),
        total_playtime_hours=connection.get("total_playtime_hours"),
        top_games=connection.get("top_games", []),
        synced_at=connection.get("synced_at"),
    )


@router.post("/{discord_user_id}/connections/steam/unlink", response_model=GenericSuccessResponse)
def unlink_steam_connection(discord_user_id: str) -> GenericSuccessResponse:
    store.unlink_connection(discord_user_id)
    return GenericSuccessResponse(success=True, message="Steam account unlinked")


@router.get("/{discord_user_id}/profile", response_model=UserProfile)
def get_user_profile(discord_user_id: str) -> UserProfile:
    profile = store.get_or_create_profile(discord_user_id)
    return profile


@router.patch("/{discord_user_id}/profile")
def update_user_profile(discord_user_id: str, payload: UpdateUserProfileRequest) -> dict[str, object]:
    profile = store.get_or_create_profile(discord_user_id)
    updated_fields: list[str] = []

    if payload.top_genres is not None:
        profile.top_genres = payload.top_genres
        updated_fields.append("top_genres")

    if payload.mood_preferences is not None:
        profile.mood_preferences = payload.mood_preferences
        updated_fields.append("mood_preferences")

    if payload.budget_preference is not None:
        profile.play_style["budget_preference"] = payload.budget_preference
        updated_fields.append("budget_preference")

    profile.updated_at = utc_now()
    store.update_profile(profile)
    return {"success": True, "updated_fields": updated_fields}
