import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from services.search_service import (
    MAX_PAGE_NUMBER,
    MAX_QUERY_LENGTH,
    SORT_OPTIONS,
    SUPPORTED_SOURCES,
    SearchInputError,
    match_reason,
    normalize_query,
    search_saved_players,
    supported_source_values,
)
from services.search_telemetry_service import record_search_event


logger = logging.getLogger(__name__)


def _teams(data_dir):
    path = Path(data_dir) / "nba_teams.json"
    with path.open("r", encoding="utf-8") as team_file:
        payload = json.load(team_file)
    return sorted(
        (team["abbreviation"].upper() for team in payload.get("teams", [])),
    )


def _record_view(record, normalized_query):
    return {
        "record": record,
        "reason": match_reason(record, normalized_query),
        "excerpt": (record.description or "")[:240],
    }


def register_search_routes(app):
    @app.route("/search", methods=["GET"])
    def search():
        original_query = request.args.get("q", "")
        query_for_display = original_query[:MAX_QUERY_LENGTH]
        team = request.args.get("team", "").strip().upper()
        raw_source = request.args.get("source", "").strip()
        source = raw_source
        sort = request.args.get("sort", "relevance").strip()
        raw_page = request.args.get("page", "1").strip()
        error_message = None
        normalized_query = ""
        search_page = None
        did_search = "q" in request.args
        search_unavailable = False

        team_choices = _teams(app.config["DATA_DIR"])
        source_choices = SUPPORTED_SOURCES
        database_ready = bool(app.config.get("DATABASE_ENABLED"))
        if database_ready and (did_search or raw_source):
            try:
                source_choices = supported_source_values()
            except SQLAlchemyError as exc:
                db.session.rollback()
                logger.error("Search filter choices failed (%s).", type(exc).__name__)
                error_message = "Search is temporarily unavailable. Please try again later."
                search_unavailable = True
        source_by_lower = {value.casefold(): value for value in source_choices}
        source = source_by_lower.get(raw_source.casefold(), raw_source)

        if error_message is None:
            if team and team not in team_choices:
                error_message = "Choose a valid NBA team abbreviation."
            elif source and source not in source_choices:
                error_message = "Choose a supported source."
            elif sort not in SORT_OPTIONS:
                error_message = "Choose a valid sort option."
            elif len(raw_page) > len(str(MAX_PAGE_NUMBER)):
                error_message = f"Page cannot exceed {MAX_PAGE_NUMBER}."
            elif not raw_page.isdigit() or int(raw_page) < 1:
                error_message = "Page must be a positive whole number."
            elif int(raw_page) > MAX_PAGE_NUMBER:
                error_message = f"Page cannot exceed {MAX_PAGE_NUMBER}."

        if did_search and error_message is None:
            try:
                query_for_display, normalized_query = normalize_query(original_query)
            except SearchInputError as exc:
                error_message = str(exc)

        if did_search and error_message is None and not database_ready:
            error_message = (
                "Searching saved records requires MySQL configuration. "
                "Explore and Team Intelligence remain available."
            )
            search_unavailable = True

        if did_search and error_message is None:
            requested_page = int(raw_page)
            try:
                search_page = search_saved_players(
                    normalized_query,
                    team=team or None,
                    source=source or None,
                    sort=sort,
                    page=requested_page,
                )
                if requested_page != search_page.page_number:
                    flash(
                        f"Showing the last available page ({search_page.page_number}).",
                        "info",
                    )
                    return redirect(
                        url_for(
                            "search",
                            q=query_for_display,
                            team=team,
                            source=source,
                            sort=sort,
                            page=search_page.page_number,
                        )
                    )
            except SQLAlchemyError as exc:
                db.session.rollback()
                logger.error(
                    "Saved-player search query failed (%s).",
                    type(exc).__name__,
                )
                error_message = "Search is temporarily unavailable. Please try again later."
                search_unavailable = True
                search_page = None
            if search_page is not None:
                recorded = record_search_event(
                    query_original=query_for_display,
                    query_normalized=normalized_query,
                    total_results=search_page.total_results,
                    returned_count=len(search_page.records),
                    page_number=search_page.page_number,
                    page_size=search_page.page_size,
                    sort_option=sort,
                    team_filter=team or None,
                    source_filter=source or None,
                )
                if not recorded:
                    flash(
                        "Results loaded, but this search could not be recorded for evaluation.",
                        "warning",
                    )

        status_code = 503 if search_unavailable else (400 if error_message else 200)
        return (
            render_template(
                "search/index.html",
                query=query_for_display,
                normalized_query=normalized_query,
                team=team,
                source=source,
                sort=sort,
                team_choices=team_choices,
                source_choices=source_choices,
                results=(
                    [_record_view(record, normalized_query) for record in search_page.records]
                    if search_page
                    else []
                ),
                search_page=search_page,
                error_message=error_message,
                did_search=did_search,
                database_ready=database_ready,
                database_status_message=app.config.get("DATABASE_STATUS_MESSAGE"),
                year=datetime.now(timezone.utc).year,
            ),
            status_code,
        )
