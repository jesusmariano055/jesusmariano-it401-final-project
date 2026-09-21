"""Explicit command for caching current API players for local Explore use."""

import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from services.balldontlie_service import CURRENT_ROSTER_SEASON, get_active_players


load_dotenv()


def sync_active_players(data_dir):
    """Fetch all active players through API pagination and write a normalized JSON cache."""
    players = []
    cursor = None
    while True:
        result = get_active_players(cursor)
        if result["status"] != "success":
            return result
        players.extend(result["players"])
        cursor = result.get("next_cursor")
        if not cursor:
            break

    output = {
        "source": "BALDONTLIE /v1/players/active",
        "roster_season": CURRENT_ROSTER_SEASON,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "players": players,
    }
    output_path = Path(data_dir) / "api_players.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return {"status": "success", "players": players, "output_path": str(output_path), "message": ""}


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    result = sync_active_players(project_root / "data")
    if result["status"] != "success":
        raise SystemExit(result["message"])
    print(f"Synced {len(result['players'])} active players to {result['output_path']}")