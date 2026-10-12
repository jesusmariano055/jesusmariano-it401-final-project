import json
from datetime import datetime, timezone
from pathlib import Path

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from extensions import db
from models.saved_player_record import SavedPlayerRecord
from services.balldontlie_service import ACTIVE_PLAYERS_URL, get_active_players
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


def _database_ready(app):
    return bool(app.config.get("DATABASE_ENABLED")) and bool(app.config.get("SQLALCHEMY_DATABASE_URI"))


def _valid_team_abbreviations(app):
    team_lookup = {team["abbreviation"].upper(): team for team in _load_teams(app.config["DATA_DIR"])}
    return team_lookup


def _validate_url(value):
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    raise ValueError("URL must use http:// or https://.")


def _sanitize_text(value, field_name, max_length=None):
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required.")
    if max_length and len(cleaned) > max_length:
        raise ValueError(f"{field_name} must be {max_length} characters or fewer.")
    return cleaned


def _team_label_for_record(app, team_abbreviation):
    team_lookup = _valid_team_abbreviations(app)
    team = team_lookup.get((team_abbreviation or "").upper())
    if team:
        return team["name"], team["abbreviation"]
    return None, (team_abbreviation or "").strip().upper() if team_abbreviation else None


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
            database_ready=_database_ready(app),
        )

    @app.route("/saved-players")
    def saved_players():
        search = request.args.get("search", "").strip()
        team = request.args.get("team", "").strip().upper()
        source = request.args.get("source", "").strip()
        query = SavedPlayerRecord.query

        if search:
            query = query.filter(SavedPlayerRecord.name.ilike(f"%{search}%"))
        if team:
            query = query.filter(SavedPlayerRecord.team_abbreviation == team)
        if source:
            query = query.filter(SavedPlayerRecord.source == source)

        records = query.order_by(SavedPlayerRecord.created_at.desc()).all()
        teams = sorted(
            {record.team_abbreviation for record in records if record.team_abbreviation},
            key=lambda value: (value or ""),
        )

        return render_template(
            "saved_players.html",
            records=records,
            teams=teams,
            search=search,
            selected_team=team,
            selected_source=source,
            year=_current_year(),
            database_ready=_database_ready(app),
            database_status_message=app.config.get("DATABASE_STATUS_MESSAGE"),
        )

    @app.route("/saved-players/new", methods=["GET", "POST"])
    def create_saved_player():
        if not _database_ready(app):
            flash(app.config.get("DATABASE_STATUS_MESSAGE"), "warning")
            return redirect(url_for("saved_players"))

        error_message = None
        if request.method == "POST":
            try:
                name = _sanitize_text(request.form.get("name"), "Name", max_length=150)
                description = _sanitize_text(request.form.get("description"), "Description")
                source = (request.form.get("source") or "Manual").strip() or "Manual"
                source_url = _validate_url(request.form.get("source_url") or "")
                team_abbreviation = (request.form.get("team_abbreviation") or "").strip().upper()
                team_name = None
                if team_abbreviation:
                    team_lookup = _valid_team_abbreviations(app)
                    if team_abbreviation not in team_lookup:
                        raise ValueError("Team abbreviation is not a valid NBA team.")
                    team_name = team_lookup[team_abbreviation]["name"]

                if source == "Manual":
                    existing_manual = SavedPlayerRecord.query.filter_by(
                        name=name,
                        description=description,
                        source="Manual",
                        team_abbreviation=team_abbreviation or None,
                    ).first()
                    if existing_manual is not None:
                        flash("This manual player record was already saved.", "info")
                        return redirect(url_for("saved_player_detail", record_id=existing_manual.id))

                position = (request.form.get("position") or "").strip() or None
                height = (request.form.get("height") or "").strip() or None
                weight = (request.form.get("weight") or "").strip() or None
                jersey_number = (request.form.get("jersey_number") or "").strip() or None

                record = SavedPlayerRecord(
                    name=name,
                    description=description,
                    source=source,
                    source_url=source_url,
                    external_player_id=None,
                    team_name=team_name,
                    team_abbreviation=team_abbreviation or None,
                    position=position,
                    height=height,
                    weight=weight,
                    jersey_number=jersey_number,
                )
                db.session.add(record)
                db.session.commit()
                flash("Saved player record created.", "success")
                return redirect(url_for("saved_player_detail", record_id=record.id))
            except ValueError as exc:
                db.session.rollback()
                error_message = str(exc)
                flash(error_message, "error")
            except IntegrityError:
                db.session.rollback()
                error_message = "This record could not be saved because of a database conflict."
                flash(error_message, "error")

        return render_template(
            "saved_player_form.html",
            record=None,
            title="Create a saved player record",
            action_url=url_for("create_saved_player"),
            year=_current_year(),
            database_ready=_database_ready(app),
            database_status_message=app.config.get("DATABASE_STATUS_MESSAGE"),
            selected_team=request.form.get("team_abbreviation", "") if request.method == "POST" else "",
            error_message=error_message,
        )

    @app.route("/saved-players/import", methods=["POST"])
    def import_saved_player():
        if not _database_ready(app):
            flash(app.config.get("DATABASE_STATUS_MESSAGE"), "warning")
            return redirect(url_for("team_intelligence"))

        player_id = (request.form.get("player_id") or "").strip()
        if not player_id:
            flash("A valid BALDONTLIE player ID is required.", "error")
            return redirect(url_for("team_intelligence"))

        api_result = get_active_players()
        if api_result.get("status") not in {"success", "empty"}:
            flash(api_result.get("message") or "BALDONTLIE is currently unavailable.", "warning")
            return redirect(url_for("team_intelligence"))

        matching_player = None
        for player in api_result.get("players", []):
            if str(player.get("player_id")) == str(player_id):
                matching_player = player
                break

        if matching_player is None:
            flash("No matching player was found with the selected BALDONTLIE ID.", "error")
            return redirect(url_for("team_intelligence"))

        team_name = matching_player.get("team_name") or "Unknown team"
        team_abbreviation = (matching_player.get("team_abbreviation") or "").strip().upper() or None
        if team_abbreviation:
            team_lookup = _valid_team_abbreviations(app)
            if team_abbreviation in team_lookup:
                team_name = team_lookup[team_abbreviation]["name"]

        data = {
            "name": matching_player.get("player_name") or "Unnamed player",
            "description": (
                f"Imported BALDONTLIE roster record for {matching_player.get('player_name') or 'this player'}. "
                f"Position: {matching_player.get('position') or 'Not listed'}; team: {team_name}."
            ),
            "source": "BALDONTLIE",
            "source_url": api_result.get("source_url") or ACTIVE_PLAYERS_URL,
            "retrieved_at": datetime.now(timezone.utc),
            "external_player_id": int(player_id),
            "team_name": team_name,
            "team_abbreviation": team_abbreviation,
            "position": matching_player.get("position") or None,
            "height": matching_player.get("height") or None,
            "weight": matching_player.get("weight") or None,
            "jersey_number": matching_player.get("jersey_number") or None,
        }

        try:
            record = SavedPlayerRecord.query.filter_by(source="BALDONTLIE", external_player_id=int(player_id)).first()
            if record is not None:
                flash(f"This player was already saved: <a href=\"{url_for('saved_player_detail', record_id=record.id)}\">View record</a>", "info")
                return redirect(url_for("saved_players"))

            saved = SavedPlayerRecord(
                name=data["name"],
                description=data["description"],
                source=data["source"],
                source_url=data["source_url"],
                retrieved_at=data["retrieved_at"],
                created_at=datetime.now(timezone.utc),
                external_player_id=data["external_player_id"],
                team_name=data["team_name"],
                team_abbreviation=data["team_abbreviation"],
                position=data["position"],
                height=data["height"],
                weight=data["weight"],
                jersey_number=data["jersey_number"],
            )
            db.session.add(saved)
            db.session.commit()
            flash("BALDONTLIE player record saved successfully.", "success")
            return redirect(url_for("saved_player_detail", record_id=saved.id))
        except IntegrityError:
            db.session.rollback()
            existing = SavedPlayerRecord.query.filter_by(source="BALDONTLIE", external_player_id=int(player_id)).first()
            if existing:
                flash("This player was already saved and is now linked in the saved-player list.", "info")
                return redirect(url_for("saved_player_detail", record_id=existing.id))
            flash("A duplicate BALDONTLIE import was rejected.", "error")
            return redirect(url_for("team_intelligence"))

    @app.route("/saved-players/<int:record_id>")
    def saved_player_detail(record_id):
        record = SavedPlayerRecord.query.get_or_404(record_id)
        return render_template(
            "saved_player_detail.html",
            record=record,
            year=_current_year(),
            database_ready=_database_ready(app),
            database_status_message=app.config.get("DATABASE_STATUS_MESSAGE"),
        )

    @app.route("/saved-players/<int:record_id>/edit", methods=["GET", "POST"])
    def edit_saved_player(record_id):
        if not _database_ready(app):
            flash(app.config.get("DATABASE_STATUS_MESSAGE"), "warning")
            return redirect(url_for("saved_players"))

        record = SavedPlayerRecord.query.get_or_404(record_id)
        if request.method == "POST":
            try:
                name = _sanitize_text(request.form.get("name"), "Name", max_length=150)
                description = _sanitize_text(request.form.get("description"), "Description")
                source_url = _validate_url(request.form.get("source_url") or "")
                team_abbreviation = (request.form.get("team_abbreviation") or "").strip().upper()
                if team_abbreviation:
                    team_lookup = _valid_team_abbreviations(app)
                    if team_abbreviation not in team_lookup:
                        raise ValueError("Team abbreviation is not a valid NBA team.")
                    record.team_name = team_lookup[team_abbreviation]["name"]
                    record.team_abbreviation = team_abbreviation
                else:
                    record.team_name = None
                    record.team_abbreviation = None

                record.name = name
                record.description = description
                record.source_url = source_url
                record.position = (request.form.get("position") or "").strip() or None
                record.height = (request.form.get("height") or "").strip() or None
                record.weight = (request.form.get("weight") or "").strip() or None
                record.jersey_number = (request.form.get("jersey_number") or "").strip() or None
                record.updated_at = datetime.now(timezone.utc)
                db.session.commit()
                flash("Saved player record updated.", "success")
                return redirect(url_for("saved_player_detail", record_id=record.id))
            except ValueError as exc:
                db.session.rollback()
                flash(str(exc), "error")

        return render_template(
            "saved_player_form.html",
            record=record,
            title="Edit saved player record",
            action_url=url_for("edit_saved_player", record_id=record.id),
            year=_current_year(),
            database_ready=_database_ready(app),
            database_status_message=app.config.get("DATABASE_STATUS_MESSAGE"),
            selected_team=record.team_abbreviation or "",
        )

    @app.route("/saved-players/<int:record_id>/delete", methods=["GET", "POST"])
    def delete_saved_player(record_id):
        if not _database_ready(app):
            flash(app.config.get("DATABASE_STATUS_MESSAGE"), "warning")
            return redirect(url_for("saved_players"))

        record = SavedPlayerRecord.query.get_or_404(record_id)
        if request.method == "POST":
            db.session.delete(record)
            db.session.commit()
            flash("Saved player record deleted.", "success")
            return redirect(url_for("saved_players"))

        return render_template(
            "saved_player_delete.html",
            record=record,
            year=_current_year(),
            database_ready=_database_ready(app),
            database_status_message=app.config.get("DATABASE_STATUS_MESSAGE"),
        )
