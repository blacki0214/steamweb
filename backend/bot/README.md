# Discord Bot (MVP)

Discord slash-command bot for the Indie Game Discovery API.

## Features

- Daily scheduled digest posts SteamDB-driven sections: trending games, hot releases, popular releases, new games, and releases today.
- `/login`: login/connect Steam account; after successful link, bot posts your Steam profile details automatically in channel.
- `/nenchoigi`: recommend games by genre/type, with Steam + Reddit review context and YouTube video links.

## Setup

1. Create and activate a Python environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Configure environment variables in `.env`.
4. Run:
   - `python bot.py`

## Test On Your Discord Server

1. Create app and bot in Discord Developer Portal.
2. Enable these Bot settings:
   - Presence Intent: optional
   - Server Members Intent: optional
   - Message Content Intent: not required for slash-only bot
3. Put values in `.env`:
   - `DISCORD_BOT_TOKEN`
   - `DISCORD_CLIENT_ID`
   - `BOT_SERVICE_TOKEN`
   - `BACKEND_BASE_URL`
4. Generate invite URL:
   - `python generate_invite_url.py`
5. Open printed URL, choose your server, authorize bot.
6. (Recommended for fast slash command sync) set `DISCORD_GUILD_ID` to your server ID.
7. Start backend API, then run bot:
   - `python bot.py`
8. In Discord, test these commands:
   - `/login`
   - `/nenchoigi`

## Environment Variables

- `DISCORD_BOT_TOKEN`: Discord bot token
- `DISCORD_CLIENT_ID`: Discord application client ID
- `BACKEND_BASE_URL`: API base URL (preferred), example `http://localhost:8001/api/v1`
- `PUBLIC_API_BASE_URL`: optional fallback if `BACKEND_BASE_URL` is not set; bot appends `/api/v1`
- `BOT_SERVICE_TOKEN`: backend service token used in `Authorization: Bearer ...`
- `STEAM_REDIRECT_URI`: OAuth redirect URI used by connect flow
- `DISCORD_GUILD_ID` (optional): for fast command sync in a single guild

## Notes

- Bot commands call backend APIs directly; business logic stays in backend.
- Current implementation uses ephemeral responses where appropriate.
