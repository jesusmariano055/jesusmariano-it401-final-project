import json
from datetime import datetime, timezone
from pathlib import Path

from flask import render_template, request


def _current_year():
    return datetime.now(timezone.utc).year


def _load_players(data_dir):
    data_file = Path(data_dir) / "players.json"
    with data_file.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return payload.get("players", [])


def register_routes(app):
    @app.route("/")
    def index():
        return render_template("index.html", year=_current_year())

    @app.route("/explore")
    def explore():
        players = _load_players(app.config["DATA_DIR"])

        search = request.args.get("search", "").strip()
        team = request.args.get("team", "").strip()
        position = request.args.get("position", "").strip()
        min_ppg = request.args.get("min_ppg", "")
        sort_ppg = request.args.get("sort_ppg", "")

        if search:
            search_lower = search.lower()
            players = [
                player for player in players if search_lower in player.get("name", "").lower()
            ]

        if team:
            players = [player for player in players if player.get("team") == team]

        if position:
            players = [player for player in players if player.get("position") == position]

        if min_ppg and min_ppg != "":
            try:
                min_ppg_value = float(min_ppg)
                players = [player for player in players if float(player.get("ppg", 0)) >= min_ppg_value]
            except ValueError:
                min_ppg_value = None

        if sort_ppg == "desc":
            players = sorted(players, key=lambda player: float(player.get("ppg", 0)), reverse=True)

        teams = sorted({player.get("team") for player in players if player.get("team")})
        positions = ["Guard", "Forward", "Center"]

        return render_template(
            "explore.html",
            players=players,
            teams=sorted({player.get("team") for player in _load_players(app.config["DATA_DIR"])}),
            positions=positions,
            search=search,
            selected_team=team,
            selected_position=position,
            min_ppg=min_ppg,
            sort_ppg=sort_ppg,
            year=_current_year(),
        )
