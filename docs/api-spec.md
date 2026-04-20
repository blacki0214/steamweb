# API Spec

This document describes the current API surface at a practical level. It is not a formal OpenAPI export, but it reflects the routes the product currently depends on.

Base path:

- `/api/v1`

Auth model:

- bot-facing endpoints use bearer-token protection through `BOT_SERVICE_TOKEN`

## Health

### `GET /health`

Purpose:

- simple service health check

Response:

```json
{
  "status": "ok"
}
```

## Auth

### `POST /auth/steam/connect-link`

Purpose:

- create a Steam connect URL for a Discord user

Request:

```json
{
  "discord_user_id": "1234567890",
  "discord_guild_id": "9876543210",
  "redirect_uri": "https://example.com/auth/steam/callback"
}
```

Response shape:

- `connect_url`
- `state`
- `expires_at`

### `GET /auth/steam/start`

Purpose:

- redirect into the Steam OpenID flow

### `GET /auth/steam/callback`

Purpose:

- complete Steam OpenID flow
- store Steam connection and summary stats
- return success HTML page

## Users

### `GET /users/{discord_user_id}/connections/steam`

Purpose:

- fetch Steam connection status for a Discord user

Includes:

- connection state
- profile metadata
- top games
- total games
- total playtime

### `POST /users/{discord_user_id}/connections/steam/unlink`

Purpose:

- remove Steam connection and related profile stats

### `GET /users/{discord_user_id}/profile`

Purpose:

- fetch or create user profile state

### `PATCH /users/{discord_user_id}/profile`

Purpose:

- update user preference fields such as genres, moods, or budget style

## Games

### `GET /games/search`

Query params:

- `query`
- `limit`

Purpose:

- search for games by title

### `GET /games/{game_id}`

Purpose:

- fetch game detail payload

Current note:

- this area still needs richer DB-backed implementation

## Search

### `GET /search`

Query params:

- `query`
- `limit`

Purpose:

- semantic-style lightweight search across title, genres, and description

## Reviews

### `GET /reviews/{game_id}`

Purpose:

- return summary review information for a given game

Current note:

- current response is still closer to MVP/demo behavior than a full aggregated summary service

## Recommendations

### `POST /recommendations/generate`

Purpose:

- generate personalized recommendations using session intent and options

Request shape:

```json
{
  "discord_user_id": "1234567890",
  "session_intent": {
    "genre": ["roguelike"],
    "mood": ["intense"],
    "session_length_minutes": 60,
    "budget": {
      "mode": "under_price",
      "currency": "USD",
      "max_price": 20
    },
    "multiplayer": "solo"
  },
  "options": {
    "top_n": 3,
    "exclude_owned": false,
    "exclude_already_played": true,
    "include_video": true,
    "include_review_summary": true,
    "relevance_mode": "medium"
  }
}
```

Response includes:

- `request_id`
- `generated_at`
- ranked recommendations
- score
- reasons
- Steam and YouTube links
- review summary context

### `POST /recommendations/refine`

Purpose:

- refine recommendations from a previous request snapshot

### `GET /recommendations/explain`

Query params:

- `discord_user_id`
- `game_id`

Purpose:

- return score breakdown and explanation payload

### `GET /recommendations/tag-options`

Query params:

- `query`
- `limit`

Purpose:

- return normalized recommendation tag suggestions for bot autocomplete

## Feedback

### `POST /feedback`

Purpose:

- store feedback events such as like, dislike, already-played, or click behavior

## Reports

### `GET /reports/daily-steam`

Query params:

- `limit`
- `realtime`

Purpose:

- build the daily Steam digest payload used by the Discord bot

Sections include:

- most played games
- trending games
- hot releases
- popular releases
- new games this week
- releases today

## Planned API Expansion

The next API surface likely needed for the website is:

- `GET /discovery/home`
- `GET /discovery/trending`
- `GET /discovery/hot-releases`
- `GET /discovery/new-releases`

Those routes are better suited to the web product than the current digest-shaped reporting route.
