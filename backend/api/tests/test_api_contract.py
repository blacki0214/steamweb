from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
BOT_HEADERS = {"Authorization": "Bearer dev-bot-token"}


def test_health_is_public() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_protected_endpoint_requires_auth() -> None:
    response = client.get("/api/v1/games/search", params={"query": "hades"})
    assert response.status_code == 401


def test_connect_link_and_callback_flow() -> None:
    link_response = client.post(
        "/api/v1/auth/steam/connect-link",
        headers=BOT_HEADERS,
        json={
            "discord_user_id": "123456",
            "discord_guild_id": "9999",
            "redirect_uri": "https://example.com/auth/steam/callback",
        },
    )
    assert link_response.status_code == 200
    assert "/api/v1/auth/steam/start?state=" in link_response.json()["connect_url"]

    state = link_response.json()["state"]
    callback_response = client.get(
        "/api/v1/auth/steam/callback",
        params={
            "state": state,
            "openid.claimed_id": "https://steamcommunity.com/openid/id/76561198000000000",
        },
    )
    assert callback_response.status_code == 200
    assert "Steam account linked successfully" in callback_response.text


def test_generate_recommendations_contract() -> None:
    response = client.post(
        "/api/v1/recommendations/generate",
        headers=BOT_HEADERS,
        json={
            "discord_user_id": "123456",
            "session_intent": {
                "genre": ["roguelike"],
                "mood": ["intense"],
                "session_length_minutes": 45,
                "budget": {"mode": "under_price", "currency": "USD", "max_price": 15},
                "multiplayer": "solo",
            },
            "options": {
                "top_n": 3,
                "exclude_owned": False,
                "exclude_already_played": True,
                "include_video": True,
                "include_review_summary": True,
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert len(data["recommendations"]) >= 1


def test_feedback_idempotency() -> None:
    payload = {
        "discord_user_id": "123456",
        "game_id": "steam_1145360",
        "feedback_type": "like",
        "context": {"request_id": "req_test", "rank": 1},
    }
    headers = {**BOT_HEADERS, "Idempotency-Key": "idem-1"}

    first = client.post("/api/v1/feedback", headers=headers, json=payload)
    second = client.post("/api/v1/feedback", headers=headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["message"] == "Feedback already recorded"
