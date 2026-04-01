from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import discord
import httpx
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")
BOT_SERVICE_TOKEN = os.getenv("BOT_SERVICE_TOKEN", "")
STEAM_REDIRECT_URI = os.getenv("STEAM_REDIRECT_URI", "http://localhost:3000/auth/steam/callback")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "").strip()
DAILY_DIGEST_CHANNEL_ID = os.getenv("DAILY_DIGEST_CHANNEL_ID", "").strip()
DAILY_DIGEST_HOUR_UTC = int(os.getenv("DAILY_DIGEST_HOUR_UTC", "8"))
DAILY_DIGEST_MINUTE_UTC = int(os.getenv("DAILY_DIGEST_MINUTE_UTC", "0"))
DAILY_DIGEST_ENABLED = os.getenv("DAILY_DIGEST_ENABLED", "true").lower() == "true"

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
        self.headers = {
            "Authorization": f"Bearer {bot_service_token}",
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

    async def refine(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/recommendations/refine", json=payload)

    async def explain(self, discord_user_id: str, game_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/recommendations/explain",
            params={"discord_user_id": discord_user_id, "game_id": game_id},
        )

    async def feedback(self, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/feedback",
            json=payload,
            headers={"Idempotency-Key": idempotency_key},
        )

    async def unlink(self, discord_user_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/users/{discord_user_id}/connections/steam/unlink")

    async def get_steam_connection(self, discord_user_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/users/{discord_user_id}/connections/steam")

    async def get_daily_steam_digest(self, limit: int = 10) -> dict[str, Any]:
        return await self._request("GET", "/reports/daily-steam", params={"limit": limit})


class IndieBot(commands.Bot):
    def __init__(self, api: ApiClient) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.api = api
        self.daily_digest_task: asyncio.Task[None] | None = None

    async def setup_hook(self) -> None:
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=int(DISCORD_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} guild commands")
        else:
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
        video = (rec.get("sources") or {}).get("youtube_video_url") or "N/A"
        lines.append(f"- {title} ({game_id}) | score={score:.2f} | {reason} | video: {video}")
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


def _compact_stat_line(item: dict[str, Any]) -> str:
    name = str(item.get("name") or "Unknown")
    app_id = item.get("app_id")
    steam = item.get("steam_reviews") or {}
    reddit = item.get("reddit") or {}

    total_reviews = steam.get("total_reviews") or 0
    positive_reviews = steam.get("positive_reviews") or 0
    reddit_posts = reddit.get("posts") or 0

    if isinstance(app_id, int):
        return (
            f"[{name}](https://store.steampowered.com/app/{app_id}) "
            f"| steam {positive_reviews}/{total_reviews} | reddit {reddit_posts}"
        )
    return f"{name} | steam {positive_reviews}/{total_reviews} | reddit {reddit_posts}"


def build_daily_digest_embed(payload: dict[str, Any]) -> discord.Embed:
    top_10 = payload.get("top_10") or {}
    generated_at = str(payload.get("generated_at") or "")

    embed = discord.Embed(
        title="Daily Steam Radar",
        description="Top 10 snapshot from Steam trends + your ingested social/review signals.",
        color=discord.Color.orange(),
    )

    sections = [
        ("Trending", "trending_games"),
        ("Hot Releases", "hot_releases"),
        ("Popular Releases", "popular_releases"),
        ("New This Week", "new_games_this_week"),
        ("Release Today", "releases_today"),
    ]

    for title, key in sections:
        items = top_10.get(key) or []
        if not isinstance(items, list) or not items:
            embed.add_field(name=title, value="No data yet", inline=False)
            continue

        lines = [f"{idx}. {_compact_stat_line(item)}" for idx, item in enumerate(items[:10], start=1)]
        embed.add_field(name=title, value="\n".join(lines), inline=False)

    if generated_at:
        embed.set_footer(text=f"Generated at: {generated_at}")
    return embed


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


async def post_daily_digest(bot_instance: "IndieBot") -> None:
    if not DAILY_DIGEST_CHANNEL_ID:
        return

    try:
        channel_id = int(DAILY_DIGEST_CHANNEL_ID)
    except ValueError:
        print("DAILY_DIGEST_CHANNEL_ID is invalid; expected integer Discord channel id")
        return

    payload = await bot_instance.api.get_daily_steam_digest(limit=10)
    embed = build_daily_digest_embed(payload)

    channel = bot_instance.get_channel(channel_id)
    if channel is None:
        channel = await bot_instance.fetch_channel(channel_id)

    await channel.send(content="Daily Steam update", embed=embed)


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

                embed = build_steam_profile_embed(data)
                await channel.send(
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
    print(f"Logged in as {bot.user} (ID: {bot.user.id if bot.user else 'unknown'})")
    if DAILY_DIGEST_ENABLED and DAILY_DIGEST_CHANNEL_ID and bot.daily_digest_task is None:
        bot.daily_digest_task = bot.loop.create_task(run_daily_digest_loop(bot))
        print("Daily digest loop started")


@bot.tree.command(name="ping", description="Check if bot is alive")
async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("pong", ephemeral=True)


@bot.tree.command(name="connect_steam", description="Get your Steam connect link")
async def connect_steam(interaction: discord.Interaction) -> None:
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


@bot.tree.command(name="login", description="Alias for Steam login/connect")
async def login(interaction: discord.Interaction) -> None:
    await connect_steam(interaction)


@bot.tree.command(name="daily_digest_now", description="Post Steam daily digest now (server message)")
async def daily_digest_now(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    try:
        await post_daily_digest(bot)
        await interaction.followup.send("Daily digest posted.", ephemeral=True)
    except ApiError as exc:
        await interaction.followup.send(
            f"Daily digest failed ({exc.status_code}): {exc.detail}",
            ephemeral=True,
        )
    except Exception as exc:
        await interaction.followup.send(f"Daily digest failed: {exc}", ephemeral=True)


@bot.tree.command(name="recommend", description="Get indie game recommendations")
@app_commands.describe(
    genre="Pick a genre from the list",
    mood="Pick a mood from the list",
    session_minutes="How many minutes you can play",
    max_price="Maximum price in USD",
    top_n="How many recommendations (1-5)",
    relevance_mode="Recommendation mode: quality vs variety",
)
@app_commands.choices(genre=GENRE_CHOICES, mood=MOOD_CHOICES, relevance_mode=RELEVANCE_MODE_CHOICES)
async def recommend(
    interaction: discord.Interaction,
    genre: app_commands.Choice[str] | None = None,
    mood: app_commands.Choice[str] | None = None,
    session_minutes: int = 60,
    max_price: float = 20,
    top_n: int = 3,
    relevance_mode: app_commands.Choice[str] | None = None,
) -> None:
    await interaction.response.defer(ephemeral=True)

    # Guardrails for static-typing compatibility and safe command input handling.
    session_minutes = max(15, min(240, session_minutes))
    max_price = max(0.0, min(100.0, max_price))
    top_n = max(1, min(5, top_n))

    # If genre/mood are omitted, show interactive selectors so users can discover available options.
    if genre is None or mood is None:
        view = RecommendConfigView(api=bot.api, discord_user_id=str(interaction.user.id))
        await interaction.followup.send(
            "Choose your Genre and Mood from the dropdowns, then click **Recommend Now**.",
            view=view,
            ephemeral=True,
        )
        return

    payload = build_recommend_payload(
        discord_user_id=str(interaction.user.id),
        genre=genre.value,
        mood=mood.value,
        session_minutes=session_minutes,
        max_price=max_price,
        top_n=top_n,
        relevance_mode=relevance_mode.value if relevance_mode else "medium",
    )

    try:
        data = await bot.api.recommend(payload)
        await interaction.followup.send(format_recommendation_text(data), ephemeral=True)
    except ApiError as exc:
        await interaction.followup.send(f"Recommend failed ({exc.status_code}): {exc.detail}", ephemeral=True)


@bot.tree.command(name="refine", description="Refine a previous recommendation request")
@app_commands.describe(base_request_id="Previous request ID", exclude_game_id="Game ID to exclude")
async def refine(interaction: discord.Interaction, base_request_id: str, exclude_game_id: str) -> None:
    await interaction.response.defer(ephemeral=True)
    payload = {
        "discord_user_id": str(interaction.user.id),
        "base_request_id": base_request_id,
        "adjustments": {"exclude_game_ids": [exclude_game_id]},
    }

    try:
        data = await bot.api.refine(payload)
        lines = [f"Refined request: {data.get('request_id', 'unknown')}"]
        for rec in data.get("recommendations", []):
            lines.append(f"- {rec.get('title', 'Unknown')} ({rec.get('game_id', '-')})")
        await interaction.followup.send("\n".join(lines), ephemeral=True)
    except ApiError as exc:
        await interaction.followup.send(f"Refine failed ({exc.status_code}): {exc.detail}", ephemeral=True)


@bot.tree.command(name="why", description="Explain why a game is recommended")
@app_commands.describe(game_id="Game ID, e.g. steam_1145360")
async def why(interaction: discord.Interaction, game_id: str) -> None:
    await interaction.response.defer(ephemeral=True)
    try:
        data = await bot.api.explain(str(interaction.user.id), game_id)
        explanation = data.get("explanation", {})
        reasons = explanation.get("human_reasons", [])
        breakdown = explanation.get("score_breakdown", {})
        msg = (
            f"Why {game_id}:\n"
            f"Reasons: {', '.join(reasons) if reasons else 'N/A'}\n"
            f"Breakdown: {breakdown}"
        )
        await interaction.followup.send(msg, ephemeral=True)
    except ApiError as exc:
        await interaction.followup.send(f"Explain failed ({exc.status_code}): {exc.detail}", ephemeral=True)


_feedback_choices = [
    app_commands.Choice(name="like", value="like"),
    app_commands.Choice(name="dislike", value="dislike"),
    app_commands.Choice(name="already_played", value="already_played"),
    app_commands.Choice(name="clicked_video", value="clicked_video"),
    app_commands.Choice(name="clicked_store", value="clicked_store"),
    app_commands.Choice(name="wishlist_added", value="wishlist_added"),
]


@bot.tree.command(name="feedback", description="Send recommendation feedback")
@app_commands.describe(game_id="Game ID", feedback_type="Feedback type", request_id="Recommendation request ID")
@app_commands.choices(feedback_type=_feedback_choices)
async def feedback(
    interaction: discord.Interaction,
    game_id: str,
    feedback_type: app_commands.Choice[str],
    request_id: str,
) -> None:
    await interaction.response.defer(ephemeral=True)

    payload = {
        "discord_user_id": str(interaction.user.id),
        "game_id": game_id,
        "feedback_type": feedback_type.value,
        "context": {"request_id": request_id},
    }
    idempotency_key = f"{interaction.user.id}:{game_id}:{feedback_type.value}:{request_id}"

    try:
        data = await bot.api.feedback(payload, idempotency_key=idempotency_key)
        await interaction.followup.send(data.get("message", "Feedback sent"), ephemeral=True)
    except ApiError as exc:
        await interaction.followup.send(f"Feedback failed ({exc.status_code}): {exc.detail}", ephemeral=True)


@bot.tree.command(name="unlink_steam", description="Unlink your Steam account")
async def unlink_steam(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    try:
        data = await bot.api.unlink(str(interaction.user.id))
        await interaction.followup.send(data.get("message", "Unlinked"), ephemeral=True)
    except ApiError as exc:
        await interaction.followup.send(f"Unlink failed ({exc.status_code}): {exc.detail}", ephemeral=True)


@bot.tree.command(name="steam_profile", description="Show your linked Steam stats in server")
async def steam_profile(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=False)
    try:
        data = await bot.api.get_steam_connection(str(interaction.user.id))
        if not data.get("is_connected"):
            await interaction.followup.send(
                "You have not linked Steam yet. Use /connect_steam first.",
                ephemeral=False,
            )
            return

        steam_id = str(data.get("steam_id") or "N/A")
        persona = str(data.get("persona_name") or interaction.user.display_name)
        profile_url = str(data.get("profile_url") or "")
        avatar_url = str(data.get("avatar_url") or "")
        total_games = data.get("total_games")
        total_playtime = data.get("total_playtime_hours")
        top_games = data.get("top_games") or []

        embed = discord.Embed(
            title=f"Steam Profile: {persona}",
            description=f"Steam ID: `{steam_id}`",
            color=discord.Color.blue(),
        )

        if profile_url:
            embed.url = profile_url
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        embed.add_field(name="Total Games", value=str(total_games or "N/A"), inline=True)
        embed.add_field(name="Playtime (hours)", value=str(total_playtime or "N/A"), inline=True)

        if top_games:
            top_lines = []
            for game in top_games[:5]:
                name = str(game.get("name") or "Unknown")
                hours = game.get("hours") or 0
                top_lines.append(f"- {name}: {hours}h")
            embed.add_field(name="Top Played Games", value="\n".join(top_lines), inline=False)

        synced_at = data.get("synced_at")
        if synced_at:
            embed.set_footer(text=f"Last synced: {synced_at}")

        await interaction.followup.send(embed=embed, ephemeral=False)
    except ApiError as exc:
        await interaction.followup.send(
            f"Steam profile failed ({exc.status_code}): {exc.detail}",
            ephemeral=False,
        )


def validate_env() -> None:
    missing = []
    if not DISCORD_BOT_TOKEN:
        missing.append("DISCORD_BOT_TOKEN")
    if not BOT_SERVICE_TOKEN:
        missing.append("BOT_SERVICE_TOKEN")

    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")


if __name__ == "__main__":
    validate_env()
    bot.run(DISCORD_BOT_TOKEN)
