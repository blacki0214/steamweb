from __future__ import annotations

from typing import Any

import httpx


class SteamRealtimeService:
	"""Fetches trending Steam titles from public SteamSpy endpoints."""

	_TOP_GAMES_URL = "https://steamspy.com/api.php"

	def fetch_trending_games(self) -> list[dict[str, Any]]:
		params = {"request": "top100in2weeks"}
		with httpx.Client(timeout=15) as client:
			response = client.get(self._TOP_GAMES_URL, params=params)
			response.raise_for_status()
			payload = response.json()

		if not isinstance(payload, dict):
			return []

		items: list[dict[str, Any]] = []
		for appid, raw in payload.items():
			if not isinstance(raw, dict):
				continue

			tags_raw = raw.get("tags", {})
			if isinstance(tags_raw, dict):
				tags = [str(tag).lower() for tag in tags_raw.keys()]
			elif isinstance(tags_raw, list):
				tags = [str(tag).lower() for tag in tags_raw]
			else:
				tags = []

			price_cents = raw.get("price", 0)
			try:
				price_value = float(price_cents) / 100 if price_cents is not None else 0.0
			except (TypeError, ValueError):
				price_value = 0.0

			positive = int(raw.get("positive", 0) or 0)
			negative = int(raw.get("negative", 0) or 0)

			items.append(
				{
					"appid": str(appid),
					"name": str(raw.get("name") or f"Steam Game {appid}"),
					"tags": tags,
					"price": price_value,
					"is_free": bool(raw.get("is_free", False)),
					"owners": str(raw.get("owners", "0")),
					"positive": positive,
					"negative": negative,
				}
			)

		return items


steam_realtime_service = SteamRealtimeService()
