# Discord Bot (MVP)

Discord slash-command bot for the Indie Game Discovery API.

## Features

- `/connect_steam`: get Steam connect URL
- `/recommend`: request personalized recommendations
- `/refine`: refine previous recommendation request
- `/why`: explain why a game is recommended
- `/feedback`: send feedback signal
- `/unlink_steam`: unlink Steam account

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
   - `/ping`
   - `/connect_steam`
   - `/recommend`
   - `/feedback`

## Environment Variables

- `DISCORD_BOT_TOKEN`: Discord bot token
- `DISCORD_CLIENT_ID`: Discord application client ID
- `BACKEND_BASE_URL`: API base URL, default `http://localhost:8000/api/v1`
- `BOT_SERVICE_TOKEN`: backend service token used in `Authorization: Bearer ...`
- `STEAM_REDIRECT_URI`: OAuth redirect URI used by connect flow
- `DISCORD_GUILD_ID` (optional): for fast command sync in a single guild

## Notes

- Bot commands call backend APIs directly; business logic stays in backend.
- Current implementation uses ephemeral responses where appropriate.
