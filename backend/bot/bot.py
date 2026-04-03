from __future__ import annotations

import asyncio
import os
import socket
import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import discord
import httpx
from discord import app_commands
from discord.ext import commands
from discord.errors import HTTPException as DiscordHTTPException, NotFound
from dotenv import load_dotenv


load_dotenv(override=True)

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
BOT_SINGLETON_PORT = int(os.getenv("BOT_SINGLETON_PORT", "8765"))
_BOT_SINGLETON_SOCKET: socket.socket | None = None


def resolve_backend_base_url() -> str:
    explicit = (os.getenv("BACKEND_BASE_URL") or "").strip()
    if explicit:
        return explicit.rstrip("/")

    public_api_base = (os.getenv("PUBLIC_API_BASE_URL") or "").strip().rstrip("/")
    if public_api_base:
        if public_api_base.endswith("/api/v1"):
            return public_api_base
        return f"{public_api_base}/api/v1"

    return "http://localhost:8000/api/v1"


BACKEND_BASE_URL = resolve_backend_base_url()
BOT_SERVICE_TOKEN = (os.getenv("BOT_SERVICE_TOKEN", "") or "").strip()
STEAM_REDIRECT_URI = os.getenv("STEAM_REDIRECT_URI", "http://localhost:3000/auth/steam/callback")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "").strip()
DAILY_DIGEST_CHANNEL_ID = os.getenv("DAILY_DIGEST_CHANNEL_ID", "").strip()
DAILY_DIGEST_HOUR_UTC = int(os.getenv("DAILY_DIGEST_HOUR_UTC", "8"))
DAILY_DIGEST_MINUTE_UTC = int(os.getenv("DAILY_DIGEST_MINUTE_UTC", "0"))
DAILY_DIGEST_ENABLED = os.getenv("DAILY_DIGEST_ENABLED", "true").lower() == "true"
USD_TO_VND_RATE = int(os.getenv("USD_TO_VND_RATE", "25000"))
ENABLE_HEALTH_SERVER = os.getenv("ENABLE_HEALTH_SERVER", "true").lower() == "true"
HEALTH_SERVER_HOST = os.getenv("HEALTH_SERVER_HOST", "0.0.0.0")
HEALTH_SERVER_PORT = int(os.getenv("PORT", "8080"))

GENRE_VALUES = [
    "roguelike",
    "metroidvania",
    "cozy",
    "simulation",
    "strategy",
    "survival",
    "platformer",
    "action",
    "rpg",
    "puzzle",
]

DEFAULT_AUTOCOMPLETE_TAGS = [
    "action",
    "adventure",
    "rpg",
    "strategy",
    "simulation",
    "survival",
    "puzzle",
    "platformer",
    "cozy",
    "roguelike",
]

MOOD_VALUES = [
    "chill",
    "intense",
    "story-rich",
    "co-op",
    "competitive",
    "relaxing",
    "dark",
    "creative",
]

GENRE_CHOICES = [app_commands.Choice(name=value.title(), value=value) for value in GENRE_VALUES]
MOOD_CHOICES = [app_commands.Choice(name=value.title(), value=value) for value in MOOD_VALUES]
RELEVANCE_MODE_VALUES = ["strict", "medium", "broad"]
RELEVANCE_MODE_CHOICES = [
    app_commands.Choice(name="Strict (quality)", value="strict"),
    app_commands.Choice(name="Medium (balanced)", value="medium"),
    app_commands.Choice(name="Broad (variety)", value="broad"),
]


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


class ApiClient:
    def __init__(self, base_url: str, bot_service_token: str) -> None:
        self.base_url = base_url
        safe_token = (bot_service_token or "").replace("\r", "").replace("\n", "").strip()
        self.headers = {
            "Authorization": f"Bearer {safe_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        merged_headers = dict(self.headers)
        if headers:
            merged_headers.update(headers)

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                json=json,
                params=params,
                headers=merged_headers,
            )

        if response.status_code >= 400:
            detail = "Request failed"
            try:
                data = response.json()
                detail = data.get("detail") or data.get("message") or detail
            except Exception:
                detail = response.text or detail
            raise ApiError(response.status_code, str(detail))

        return response.json()

    async def create_connect_link(self, discord_user_id: str, discord_guild_id: str | None) -> dict[str, Any]:
        payload = {
            "discord_user_id": discord_user_id,
            "discord_guild_id": discord_guild_id,
            "redirect_uri": STEAM_REDIRECT_URI,
        }
        return await self._request("POST", "/auth/steam/connect-link", json=payload)

    async def recommend(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/recommendations/generate", json=payload)

    async def recommendation_tag_options(self, query: str, limit: int = 25) -> dict[str, Any]:
        return await self._request("GET", "/recommendations/tag-options", params={"query": query, "limit": limit})

    async def unlink(self, discord_user_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/users/{discord_user_id}/connections/steam/unlink")

    async def get_steam_connection(self, discord_user_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/users/{discord_user_id}/connections/steam")

    async def get_daily_steam_digest(self, limit: int = 10, realtime: bool = False) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/reports/daily-steam",
            params={"limit": limit, "realtime": str(realtime).lower()},
        )


class IndieBot(commands.Bot):
    def __init__(self, api: ApiClient) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.api = api
        self.daily_digest_task: asyncio.Task[None] | None = None
        self.tag_cache_task: asyncio.Task[None] | None = None
        self._seen_interaction_ids: set[int] = set()
        self._seen_interaction_order: deque[int] = deque(maxlen=2048)
        self.recommendation_tag_cache: list[str] = []

    def mark_interaction_seen(self, interaction_id: int) -> bool:
        if interaction_id in self._seen_interaction_ids:
            return False

        if len(self._seen_interaction_order) == self._seen_interaction_order.maxlen:
            oldest = self._seen_interaction_order.popleft()
            self._seen_interaction_ids.discard(oldest)

        self._seen_interaction_order.append(interaction_id)
        self._seen_interaction_ids.add(interaction_id)
        return True

    async def setup_hook(self) -> None:
        await refresh_recommendation_tag_cache(self)
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=int(DISCORD_GUILD_ID))
            # Remove stale guild commands from previous iterations before re-sync.
            self.tree.clear_commands(guild=guild)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} guild commands")
        else:
            # Remove stale global commands from previous iterations before re-sync.
            self.tree.clear_commands(guild=None)
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} global commands")


def build_recommend_payload(
    discord_user_id: str,
    genre: str,
    mood: str,
    session_minutes: int,
    max_price: float,
    top_n: int,
    relevance_mode: str = "medium",
) -> dict[str, Any]:
    return {
        "discord_user_id": discord_user_id,
        "session_intent": {
            "genre": [genre],
            "mood": [mood],
            "session_length_minutes": session_minutes,
            "budget": {"mode": "under_price", "currency": "USD", "max_price": max_price},
            "multiplayer": "solo",
        },
        "options": {
            "top_n": top_n,
            "exclude_owned": False,
            "exclude_already_played": True,
            "include_video": True,
            "include_review_summary": True,
            "relevance_mode": relevance_mode,
        },
    }


def format_recommendation_text(data: dict[str, Any]) -> str:
    request_id = data.get("request_id", "unknown")
    recs = data.get("recommendations", [])
    if not recs:
        return "No recommendations available right now."

    lines = [f"Request ID: {request_id}"]
    for rec in recs:
        reason = rec.get("reasons", ["No reason"])[0]
        title = rec.get("title", "Unknown")
        game_id = rec.get("game_id", "-")
        score = rec.get("match_score", 0)
        sources = rec.get("sources") or {}
        video = sources.get("youtube_video_url") or "N/A"
        store_url = sources.get("steam_store_url") or "N/A"

        review_summary = sources.get("review_summary") or {}
        steam_review = review_summary.get("steam") or {}
        steam_label = steam_review.get("label") or "N/A"
        steam_sample = steam_review.get("sample_size") or 0

        reddit_review = review_summary.get("reddit") or {}
        reddit_sentiment = reddit_review.get("sentiment_score")
        reddit_highlights = reddit_review.get("highlights") or []
        reddit_line = "N/A"
        if isinstance(reddit_sentiment, (float, int)):
            reddit_line = f"sentiment={float(reddit_sentiment):.2f}"
        if isinstance(reddit_highlights, list) and reddit_highlights:
            reddit_line = f"{reddit_line} | highlights: {', '.join(str(x) for x in reddit_highlights[:2])}"

        lines.append(f"- {title} ({game_id}) | score={score:.2f} | {reason}")
        lines.append(f"  Steam review: {steam_label} (n={steam_sample})")
        lines.append(f"  Reddit review: {reddit_line}")
        lines.append(f"  YouTube: {video}")
        lines.append(f"  Store: {store_url}")
    return "\n".join(lines)


def build_steam_profile_embed(data: dict[str, Any]) -> discord.Embed:
    steam_id = str(data.get("steam_id") or "N/A")
    persona = str(data.get("persona_name") or "Steam User")
    profile_url = str(data.get("profile_url") or "")
    avatar_url = str(data.get("avatar_url") or "")
    total_games = data.get("total_games")
    total_playtime = data.get("total_playtime_hours")
    top_games = data.get("top_games") or []

    embed = discord.Embed(
        title=f"Steam Linked: {persona}",
        description=f"Steam ID: `{steam_id}`",
        color=discord.Color.green(),
    )

    if profile_url:
        embed.url = profile_url
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    embed.add_field(name="Total Games", value=str(total_games or "N/A"), inline=True)
    embed.add_field(name="Playtime (hours)", value=str(total_playtime or "N/A"), inline=True)

    if isinstance(top_games, list) and top_games:
        lines: list[str] = []
        for game in top_games[:5]:
            name = str(game.get("name") or "Unknown")
            hours = game.get("hours") or 0
            lines.append(f"- {name}: {hours}h")
        embed.add_field(name="Top Played Games", value="\n".join(lines), inline=False)

    synced_at = data.get("synced_at")
    if synced_at:
        embed.set_footer(text=f"Last synced: {synced_at}")

    return embed


def _fmt_players(value: Any) -> str:
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        return "n/a"
    return f"{ivalue:,}"


def _fmt_price_vnd(steam: dict[str, Any]) -> str:
    if bool(steam.get("is_free") or False):
        return "Free"
    raw = steam.get("price_usd")
    if raw is None:
        return "n/a"
    try:
        price = float(raw)
    except (TypeError, ValueError):
        return "n/a"
    price_vnd = round(price * max(1, USD_TO_VND_RATE))
    return f"{price_vnd:,.0f} VND"


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    if limit <= 3:
        return value[:limit]
    return value[: limit - 3] + "..."


def _compact_stat_line(item: dict[str, Any]) -> str:
    name = _truncate_text(str(item.get("name") or "Unknown"), 30)
    app_id = item.get("app_id")
    store_url = item.get("steam_store_url")
    players_label = _fmt_players(item.get("players_current"))
    steam = item.get("steam_reviews") or {}
    price_label = _fmt_price_vnd(steam)

    title = name
    if isinstance(app_id, int):
        title = f"[{name}](https://store.steampowered.com/app/{app_id})"
    elif isinstance(store_url, str) and store_url:
        title = f"[{name}]({store_url})"

    return f"{title} | players {players_label} | price {price_label}"


def _build_section_lines(items: list[dict[str, Any]], *, limit: int, max_field_chars: int) -> tuple[list[str], int]:
    # Keep each field under Discord's 1024-char limit without cutting markdown mid-link.
    max_field_chars = max(32, min(1024, max_field_chars))
    lines: list[str] = []
    used_chars = 0
    shown = 0

    for idx, item in enumerate(items[:limit], start=1):
        line = f"{idx}. {_compact_stat_line(item)}"
        additional = len(line) + (1 if lines else 0)
        if used_chars + additional > max_field_chars:
            break
        lines.append(line)
        used_chars += additional
        shown += 1

    return lines, shown


def _chunk_lines(lines: list[str], *, max_chars: int) -> list[str]:
    max_chars = max(32, min(1024, max_chars))
    chunks: list[str] = []
    current: list[str] = []
    used = 0

    for line in lines:
        add_len = len(line) + (1 if current else 0)
        if used + add_len > max_chars and current:
            chunks.append("\n".join(current))
            current = [line]
            used = len(line)
            continue

        if used + add_len > max_chars:
            # Keep markdown valid even when one single line is too long.
            current = [_truncate_text(line, max_chars)]
            used = len(current[0])
            continue

        current.append(line)
        used += add_len

    if current:
        chunks.append("\n".join(current))

    return chunks


def _format_utc_timestamp(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _format_discord_timestamp(dt: datetime) -> str:
    return f"<t:{int(dt.astimezone(timezone.utc).timestamp())}:F>"


def build_daily_digest_embeds(payload: dict[str, Any], *, posted_at_utc: datetime | None = None) -> list[discord.Embed]:
    top_10 = payload.get("top_10") or {}
    section_meta = payload.get("section_meta") or {}
    generated_at = str(payload.get("generated_at") or "")
    posted_at_utc = posted_at_utc or datetime.now(timezone.utc)
    updated_label = _format_utc_timestamp(posted_at_utc)
    updated_discord = _format_discord_timestamp(posted_at_utc)

    sections = [
        ("Most Played", "most_played_games"),
        ("Trending", "trending_games"),
        ("Hot Releases", "hot_releases"),
        ("Popular Releases", "popular_releases"),
        ("New This Week", "new_games_this_week"),
        ("Releases Today", "releases_today"),
    ]

    max_items_per_section = 10

    section_fields: list[tuple[str, str]] = []
    for title, key in sections:
        items = top_10.get(key) or []
        meta = section_meta.get(key) if isinstance(section_meta, dict) else None
        meta_line = ""
        if isinstance(meta, dict):
            source = str(meta.get("source") or "")
            snapshot_at = str(meta.get("snapshot_at") or "")
            quality = str(meta.get("quality") or "")
            meta_parts: list[str] = []
            if source:
                meta_parts.append(f"source: {source}")
            if snapshot_at:
                meta_parts.append(f"snapshot: {snapshot_at}")
            if quality and quality != "accepted":
                meta_parts.append(f"quality: {quality}")
            if meta_parts:
                meta_line = " | ".join(meta_parts)

        if not isinstance(items, list) or not items:
            empty_value = "No data yet"
            if meta_line:
                empty_value = f"{meta_line}\n{empty_value}"
            section_fields.append((title, _truncate_text(empty_value, 1024)))
            continue

        top_items = items[:max_items_per_section]
        lines = [f"{idx}. {_compact_stat_line(item)}" for idx, item in enumerate(top_items, start=1)]
        field_chunks = _chunk_lines(lines, max_chars=1024)

        if meta_line and field_chunks:
            first_budget = max(32, 1024 - (len(meta_line) + 1))
            first_lines = _chunk_lines(lines, max_chars=first_budget)
            if first_lines:
                field_chunks = [f"{meta_line}\n{first_lines[0]}"]
                remaining_lines = lines[len(first_lines[0].split("\n")):]
                if remaining_lines:
                    field_chunks.extend(_chunk_lines(remaining_lines, max_chars=1024))
            else:
                field_chunks = [_truncate_text(meta_line, 1024)]
        elif meta_line and not field_chunks:
            field_chunks = [_truncate_text(meta_line, 1024)]

        shown = len(top_items)
        remaining = max(0, min(max_items_per_section, len(items)) - shown)
        if remaining > 0:
            suffix = f"... +{remaining} more"
            if field_chunks:
                if len(field_chunks[-1]) + len("\n") + len(suffix) <= 1024:
                    field_chunks[-1] = f"{field_chunks[-1]}\n{suffix}"
            else:
                field_chunks = [suffix]

        for idx, chunk in enumerate(field_chunks):
            field_name = title if idx == 0 else f"{title} (cont.)"
            section_fields.append((field_name, _truncate_text(chunk, 1024)))

    embeds: list[discord.Embed] = []
    sections_per_embed = 2
    current_embed: discord.Embed | None = None
    sections_in_current = 0

    def _new_embed(page_idx: int) -> discord.Embed:
        page_title = "Daily Steam Radar" if page_idx == 1 else f"Daily Steam Radar (Page {page_idx})"
        return discord.Embed(
            title=page_title,
            description=(
                "Top 10 snapshot from Steam trends + your ingested social/review signals.\n"
                f"Updated: {updated_label} ({updated_discord})"
            ),
            color=discord.Color.orange(),
            timestamp=posted_at_utc,
        )

    page_idx = 1
    current_embed = _new_embed(page_idx)
    current_section_root: str | None = None

    for field_name, field_value in section_fields:
        is_new_section = not field_name.endswith("(cont.)")
        if is_new_section and sections_in_current >= sections_per_embed:
            embeds.append(current_embed)
            page_idx += 1
            current_embed = _new_embed(page_idx)
            sections_in_current = 0

        current_embed.add_field(name=field_name, value=field_value, inline=False)
        if is_new_section:
            sections_in_current += 1
            current_section_root = field_name
        elif current_section_root is None:
            current_section_root = field_name

    if generated_at:
        footer_text = f"Generated at: {generated_at}"
        if current_embed.footer and current_embed.footer.text:
            current_embed.set_footer(text=f"{current_embed.footer.text} | {footer_text}")
        else:
            current_embed.set_footer(text=footer_text)

    embeds.append(current_embed)
    return embeds


def _next_trigger_time(now: datetime) -> datetime:
    trigger = now.replace(
        hour=max(0, min(23, DAILY_DIGEST_HOUR_UTC)),
        minute=max(0, min(59, DAILY_DIGEST_MINUTE_UTC)),
        second=0,
        microsecond=0,
    )
    if trigger <= now:
        trigger = trigger + timedelta(days=1)
    return trigger


def _messageable_channel(
    channel: discord.abc.GuildChannel | discord.abc.PrivateChannel | discord.Thread | None,
) -> discord.abc.Messageable | None:
    if channel is None:
        return None
    if isinstance(channel, discord.abc.Messageable):
        return channel
    return None


async def post_daily_digest(bot_instance: "IndieBot") -> None:
    if not DAILY_DIGEST_CHANNEL_ID:
        return

    try:
        channel_id = int(DAILY_DIGEST_CHANNEL_ID)
    except ValueError:
        print("DAILY_DIGEST_CHANNEL_ID is invalid; expected integer Discord channel id")
        return

    posted_at_utc = datetime.now(timezone.utc)
    payload = await bot_instance.api.get_daily_steam_digest(limit=10, realtime=True)
    embeds = build_daily_digest_embeds(payload, posted_at_utc=posted_at_utc)

    channel = bot_instance.get_channel(channel_id)
    if channel is None:
        channel = await bot_instance.fetch_channel(channel_id)

    target = _messageable_channel(channel)
    if target is None:
        print(f"DAILY_DIGEST_CHANNEL_ID {channel_id} is not a messageable channel")
        return

    content = (
        "Daily Steam update "
        f"(UTC: {_format_utc_timestamp(posted_at_utc)} | {_format_discord_timestamp(posted_at_utc)})"
    )
    if embeds:
        await target.send(content=content, embed=embeds[0])
        for embed in embeds[1:]:
            await target.send(embed=embed)
    else:
        await target.send(content=content)


async def run_daily_digest_loop(bot_instance: "IndieBot") -> None:
    while True:
        now = datetime.now(timezone.utc)
        target = _next_trigger_time(now)
        wait_seconds = max(1, int((target - now).total_seconds()))
        await asyncio.sleep(wait_seconds)

        try:
            await post_daily_digest(bot_instance)
        except Exception as exc:
            print(f"daily digest post failed: {exc}")


async def announce_after_steam_link(
    *,
    bot_instance: commands.Bot,
    api: ApiClient,
    discord_user_id: str,
    channel_id: int,
    expires_at_iso: str,
) -> None:
    """Poll Steam connection status and announce profile in server when linked."""
    try:
        deadline = datetime.fromisoformat(expires_at_iso.replace("Z", "+00:00"))
    except Exception:
        deadline = datetime.now(timezone.utc) + timedelta(minutes=15)

    while datetime.now(timezone.utc) <= deadline:
        try:
            data = await api.get_steam_connection(discord_user_id)
            if data.get("is_connected"):
                channel = bot_instance.get_channel(channel_id)
                if channel is None:
                    channel = await bot_instance.fetch_channel(channel_id)

                target = _messageable_channel(channel)
                if target is None:
                    return

                embed = build_steam_profile_embed(data)
                await target.send(
                    content=f"<@{discord_user_id}> connected Steam successfully!",
                    embed=embed,
                )
                return
        except Exception:
            # Keep polling until deadline; transient API/Discord failures are expected.
            pass

        await asyncio.sleep(5)


class RecommendConfigView(discord.ui.View):
    def __init__(self, api: ApiClient, discord_user_id: str) -> None:
        super().__init__(timeout=300)
        self.api = api
        self.discord_user_id = discord_user_id
        self.genre: str | None = None
        self.mood: str | None = None
        self.relevance_mode: str = "medium"

        self.add_item(GenreSelect(self))
        self.add_item(MoodSelect(self))
        self.add_item(RelevanceModeSelect(self))

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, (discord.ui.Select, discord.ui.Button)):
                item.disabled = True

    @discord.ui.button(label="Recommend Now", style=discord.ButtonStyle.success)
    async def recommend_now(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not self.genre or not self.mood:
            await interaction.response.send_message("Please choose both genre and mood first.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        payload = build_recommend_payload(
            discord_user_id=self.discord_user_id,
            genre=self.genre,
            mood=self.mood,
            session_minutes=60,
            max_price=20,
            top_n=3,
            relevance_mode=self.relevance_mode,
        )
        try:
            data = await self.api.recommend(payload)
            await interaction.followup.send(format_recommendation_text(data), ephemeral=True)
        except ApiError as exc:
            await interaction.followup.send(
                f"Recommend failed ({exc.status_code}): {exc.detail}",
                ephemeral=True,
            )


class GenreSelect(discord.ui.Select):
    def __init__(self, parent_view: RecommendConfigView) -> None:
        self.parent_view = parent_view
        options = [discord.SelectOption(label=value.title(), value=value) for value in GENRE_VALUES]
        super().__init__(placeholder="Choose genre", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parent_view.genre = self.values[0]
        await interaction.response.send_message(
            f"Genre selected: {self.parent_view.genre}",
            ephemeral=True,
        )


class MoodSelect(discord.ui.Select):
    def __init__(self, parent_view: RecommendConfigView) -> None:
        self.parent_view = parent_view
        options = [discord.SelectOption(label=value.title(), value=value) for value in MOOD_VALUES]
        super().__init__(placeholder="Choose mood", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parent_view.mood = self.values[0]
        await interaction.response.send_message(
            f"Mood selected: {self.parent_view.mood}",
            ephemeral=True,
        )


class RelevanceModeSelect(discord.ui.Select):
    def __init__(self, parent_view: RecommendConfigView) -> None:
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label="Strict (quality)", value="strict"),
            discord.SelectOption(label="Medium (balanced)", value="medium", default=True),
            discord.SelectOption(label="Broad (variety)", value="broad"),
        ]
        super().__init__(placeholder="Choose relevance mode", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parent_view.relevance_mode = self.values[0]
        await interaction.response.send_message(
            f"Relevance mode selected: {self.parent_view.relevance_mode}",
            ephemeral=True,
        )


api_client = ApiClient(BACKEND_BASE_URL, BOT_SERVICE_TOKEN)
bot = IndieBot(api=api_client)


@bot.event
async def on_ready() -> None:
    print("BOT_BUILD: nenchoigi_no_defer_v2")
    print(f"BOT_API_BASE_URL: {BACKEND_BASE_URL}")
    print(f"Logged in as {bot.user} (ID: {bot.user.id if bot.user else 'unknown'})")
    if bot.tag_cache_task is None:
        bot.tag_cache_task = bot.loop.create_task(run_tag_cache_loop(bot))
        print("Recommendation tag cache loop started")
    if DAILY_DIGEST_ENABLED and DAILY_DIGEST_CHANNEL_ID and bot.daily_digest_task is None:
        bot.daily_digest_task = bot.loop.create_task(run_daily_digest_loop(bot))
        print("Daily digest loop started")


async def _start_steam_login(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    try:
        guild_id = str(interaction.guild_id) if interaction.guild_id else None
        data = await bot.api.create_connect_link(str(interaction.user.id), guild_id)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Connect Steam",
                style=discord.ButtonStyle.link,
                url=data["connect_url"],
            )
        )

        await interaction.followup.send(
            "Tap **Connect Steam** and complete login in browser.\n"
            "After successful sign-in, the bot will automatically post your Steam profile in this channel.\n"
            f"This link expires at: {data['expires_at']}",
            view=view,
            ephemeral=True,
        )

        if interaction.channel_id is not None:
            bot.loop.create_task(
                announce_after_steam_link(
                    bot_instance=bot,
                    api=bot.api,
                    discord_user_id=str(interaction.user.id),
                    channel_id=interaction.channel_id,
                    expires_at_iso=str(data["expires_at"]),
                )
            )
    except ApiError as exc:
        await interaction.followup.send(f"Connect failed ({exc.status_code}): {exc.detail}", ephemeral=True)


@bot.tree.command(name="login", description="Login and connect your Steam account")
async def login(interaction: discord.Interaction) -> None:
    await _start_steam_login(interaction)


@bot.tree.command(name="digestnow", description="Post the Daily Steam digest now in this channel")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def digestnow(interaction: discord.Interaction) -> None:
    if not bot.mark_interaction_seen(interaction.id):
        return

    if interaction.guild is None:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    member = interaction.user
    if not isinstance(member, discord.Member) or not member.guild_permissions.administrator:
        await interaction.response.send_message("Only server admins can use /digestnow.", ephemeral=True)
        return

    acked = await _ack_interaction(interaction)
    if not acked:
        return

    target = _messageable_channel(interaction.channel)
    if target is None:
        await _update_ephemeral_result(interaction, "Cannot post digest in this channel.")
        return

    try:
        payload = await bot.api.get_daily_steam_digest(limit=10, realtime=True)
    except ApiError as exc:
        await _update_ephemeral_result(
            interaction,
            f"Digest fetch failed ({exc.status_code}): {exc.detail}",
        )
        return

    posted_at_utc = datetime.now(timezone.utc)
    embeds = build_daily_digest_embeds(payload, posted_at_utc=posted_at_utc)
    content = (
        "Daily Steam update (manual trigger) "
        f"(UTC: {_format_utc_timestamp(posted_at_utc)} | {_format_discord_timestamp(posted_at_utc)})"
    )
    if embeds:
        await target.send(content=content, embed=embeds[0])
        for embed in embeds[1:]:
            await target.send(embed=embed)
    else:
        await target.send(content=content)
    await _update_ephemeral_result(interaction, "Posted Daily Steam digest in this channel.")


async def genre_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    query = current.strip().lower()
    items = bot.recommendation_tag_cache
    if not items:
        # Never return an empty list; allow manual value entry when cache is cold.
        if query:
            return [app_commands.Choice(name=query[:100], value=query)]
        return [app_commands.Choice(name="action", value="action")]

    if query:
        filtered = [x for x in items if query in x.lower()]
        if not filtered:
            # Keep UX functional even when query has no direct matches.
            filtered = [query, *items]
    else:
        filtered = items

    choices: list[app_commands.Choice[str]] = []
    for item in filtered[:25]:
        value = str(item).strip()
        if not value:
            continue
        # Discord label max length is 100.
        label = value if len(value) <= 100 else value[:97] + "..."
        choices.append(app_commands.Choice(name=label, value=value))
    return choices


async def refresh_recommendation_tag_cache(bot_instance: "IndieBot") -> None:
    try:
        data = await bot_instance.api.recommendation_tag_options(query="", limit=100)
    except Exception:
        return

    items = data.get("items", [])
    if not isinstance(items, list):
        return

    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item).strip()
        key = value.lower()
        if not value or key in seen:
            continue
        seen.add(key)
        normalized.append(value)

    merged: list[str] = []
    seen: set[str] = set()
    for value in [*normalized, *DEFAULT_AUTOCOMPLETE_TAGS]:
        token = str(value).strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        merged.append(token)

    if merged:
        bot_instance.recommendation_tag_cache = merged


async def run_tag_cache_loop(bot_instance: "IndieBot") -> None:
    while True:
        await asyncio.sleep(300)
        try:
            await refresh_recommendation_tag_cache(bot_instance)
        except Exception:
            pass


def acquire_bot_singleton_lock() -> bool:
    global _BOT_SINGLETON_SOCKET
    try:
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lock_socket.bind(("127.0.0.1", BOT_SINGLETON_PORT))
        lock_socket.listen(1)
        _BOT_SINGLETON_SOCKET = lock_socket
        return True
    except OSError:
        return False


@bot.tree.command(name="nenchoigi", description="Recommend games by genre/type with Steam+Reddit+YouTube context")
@app_commands.describe(
    genre="Pick a genre tag from DB",
    mood="Pick type/mood from the list",
    session_minutes="How many minutes you can play",
    max_price="Maximum price in USD",
    top_n="How many recommendations (1-5)",
    relevance_mode="Recommendation mode: quality vs variety",
)
@app_commands.autocomplete(genre=genre_autocomplete)
@app_commands.choices(mood=MOOD_CHOICES, relevance_mode=RELEVANCE_MODE_CHOICES)
async def nenchoigi(
    interaction: discord.Interaction,
    genre: str,
    mood: app_commands.Choice[str],
    session_minutes: int = 60,
    max_price: float = 20.0,
    top_n: int = 3,
    relevance_mode: app_commands.Choice[str] | None = None,
) -> None:
    if not bot.mark_interaction_seen(interaction.id):
        return

    try:
        await _run_recommendation_flow(
            interaction=interaction,
            genre=genre,
            mood=mood,
            session_minutes=session_minutes,
            max_price=max_price,
            top_n=top_n,
            relevance_mode=relevance_mode,
        )
    except DiscordHTTPException as exc:
        if exc.code == 40060:
            # Duplicate acknowledgement races should not crash the command handler.
            return
        raise


async def _run_recommendation_flow(
    *,
    interaction: discord.Interaction,
    genre: str,
    mood: app_commands.Choice[str],
    session_minutes: int,
    max_price: float,
    top_n: int,
    relevance_mode: app_commands.Choice[str] | None,
) -> None:
    acked = await _ack_interaction(interaction)
    if not acked:
        return

    # Guardrails for static-typing compatibility and safe command input handling.
    session_minutes = max(15, min(240, session_minutes))
    max_price = max(0.0, min(100.0, max_price))
    top_n = max(1, min(5, top_n))

    payload = build_recommend_payload(
        discord_user_id=str(interaction.user.id),
        genre=genre,
        mood=mood.value,
        session_minutes=session_minutes,
        max_price=max_price,
        top_n=top_n,
        relevance_mode=relevance_mode.value if relevance_mode else "medium",
    )

    try:
        data = await bot.api.recommend(payload)
        await _update_ephemeral_result(interaction, format_recommendation_text(data))
    except ApiError as exc:
        await _update_ephemeral_result(interaction, f"Recommend failed ({exc.status_code}): {exc.detail}")


async def _send_ephemeral(
    interaction: discord.Interaction,
    content: str,
    *,
    view: discord.ui.View | None = None,
) -> bool:
    try:
        if interaction.response.is_done():
            if view is None:
                await interaction.followup.send(content, ephemeral=True)
            else:
                await interaction.followup.send(content, view=view, ephemeral=True)
        else:
            if view is None:
                await interaction.response.send_message(content, ephemeral=True)
            else:
                await interaction.response.send_message(content, view=view, ephemeral=True)
        return True
    except NotFound:
        # Interaction expired before acknowledgement/follow-up.
        return False
    except DiscordHTTPException as exc:
        # 40060: interaction already acknowledged; use follow-up channel.
        if exc.code == 40060:
            try:
                if view is None:
                    await interaction.followup.send(content, ephemeral=True)
                else:
                    await interaction.followup.send(content, view=view, ephemeral=True)
                return True
            except Exception:
                return False
        raise
    except Exception as exc:
        # Defensive fallback for Discord race conditions surfaced via non-exported exception wrappers.
        if getattr(exc, "code", None) == 40060:
            try:
                if view is None:
                    await interaction.followup.send(content, ephemeral=True)
                else:
                    await interaction.followup.send(content, view=view, ephemeral=True)
                return True
            except Exception:
                return False
        raise


async def _ack_interaction(interaction: discord.Interaction) -> bool:
    if interaction.response.is_done():
        return True

    try:
        await interaction.response.defer(ephemeral=True)
        return True
    except NotFound:
        return False
    except DiscordHTTPException as exc:
        if exc.code == 40060:
            return True
        raise
    except Exception as exc:
        if getattr(exc, "code", None) == 40060:
            return True
        raise


async def _update_ephemeral_result(interaction: discord.Interaction, content: str) -> None:
    if not interaction.response.is_done():
        await _send_ephemeral(interaction, content)
        return

    try:
        await interaction.followup.send(content, ephemeral=True)
    except Exception:
        await _send_ephemeral(interaction, content)


def validate_env() -> None:
    missing = []
    if not DISCORD_BOT_TOKEN:
        missing.append("DISCORD_BOT_TOKEN")
    if not BOT_SERVICE_TOKEN:
        missing.append("BOT_SERVICE_TOKEN")

    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/health":
            payload = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        # Keep bot logs focused on Discord/API events.
        return


def start_health_server() -> ThreadingHTTPServer | None:
    if not ENABLE_HEALTH_SERVER:
        return None

    server = ThreadingHTTPServer((HEALTH_SERVER_HOST, HEALTH_SERVER_PORT), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Health server listening on {HEALTH_SERVER_HOST}:{HEALTH_SERVER_PORT}")
    return server


if __name__ == "__main__":
    validate_env()
    _health_server = start_health_server()
    if not acquire_bot_singleton_lock():
        raise RuntimeError(
            f"Another bot instance is already running (lock port {BOT_SINGLETON_PORT} is in use)."
        )
    bot.run(DISCORD_BOT_TOKEN)
