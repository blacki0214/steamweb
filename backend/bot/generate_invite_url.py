from __future__ import annotations

import os
from urllib.parse import urlencode

from dotenv import load_dotenv


load_dotenv()


def main() -> None:
    client_id = os.getenv("DISCORD_CLIENT_ID", "").strip()
    if not client_id:
        raise RuntimeError("Missing DISCORD_CLIENT_ID in environment")

    params = {
        "client_id": client_id,
        "scope": "bot applications.commands",
        "permissions": "274877906944",  # Send Messages + Use Slash Commands
    }
    url = f"https://discord.com/oauth2/authorize?{urlencode(params)}"
    print(url)


if __name__ == "__main__":
    main()
