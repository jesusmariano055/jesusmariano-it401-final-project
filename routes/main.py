import json
from datetime import datetime, timezone
from pathlib import Path

from flask import render_template, request

from services.team_intelligence_service import build_report


def _current_year():
    return datetime.now(timezone.utc).year


def _load_players(data_dir):
    data_file = Path(data_dir) / "players.json"
    with data_file.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return payload.get("players", [])


def _load_teams(data_dir):
    data_file = Path(data_dir) / "nba_teams.json"
    with data_file.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return payload.get("teams", [])


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

    @app.route("/team-intelligence")
    def team_intelligence():
        teams = _load_teams(app.config["DATA_DIR"])
        selected_abbreviation = request.args.get("team", "").strip().upper()
        report = None
        message = None

        if selected_abbreviation:
            selected_team = next(
                (team for team in teams if team["abbreviation"] == selected_abbreviation), None
            )
            if selected_team is None:
                message = "Please choose an NBA team from the provided list."
            else:
                report = build_report(selected_team)

        return render_template(
            "team_intelligence.html",
            teams=teams,
            selected_team=selected_abbreviation,
            report=report,
            message=message,
            year=_current_year(),
        )
