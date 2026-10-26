import os

import click
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

from config import config
from extensions import db
from routes.main import register_routes
from routes.search import register_search_routes


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)

    csrf = CSRFProtect()
    csrf.init_app(app)

    @app.cli.command("init-db")
    def init_db_command():
        if not app.config.get("DATABASE_ENABLED"):
            raise click.ClickException(
                "Database is not configured. Set MYSQL_HOST, MYSQL_DATABASE, MYSQL_USER, and MYSQL_PASSWORD before running init-db."
            )
        try:
            db.create_all()
        except SQLAlchemyError as exc:
            app.logger.error(
                "Could not initialize application tables (%s).",
                type(exc).__name__,
            )
            raise click.ClickException(
                "Application tables could not be initialized. Check the database configuration."
            ) from exc
        click.echo("Initialized CourtVision application tables.")

    register_routes(app)
    register_search_routes(app)

    @app.cli.command("search-stats")
    def search_stats_command():
        if not app.config.get("DATABASE_ENABLED"):
            raise click.ClickException("Database is not configured; search telemetry is unavailable.")
        from services.search_telemetry_service import recent_search_stats

        try:
            stats = recent_search_stats()
        except SQLAlchemyError as exc:
            app.logger.error("Could not read search telemetry (%s).", type(exc).__name__)
            raise click.ClickException("Search telemetry is temporarily unavailable.") from exc
        click.echo(f"Search events: {stats['event_count']}")
        click.echo(f"Zero-result events: {stats['zero_result_count']}")
        click.echo("Recent searches:")
        for event in stats["recent_events"]:
            click.echo(
                f"{event.searched_at.isoformat()} | {event.query_normalized!r} | "
                f"results={event.total_results} returned={event.returned_count} "
                f"page={event.page_number}"
            )

    @app.cli.command("seed-search-evaluation")
    @click.option(
        "--confirm",
        is_flag=True,
        help="Explicitly allow synthetic/manual evaluation records to be inserted.",
    )
    def seed_search_evaluation_command(confirm):
        if not app.config.get("DATABASE_ENABLED"):
            raise click.ClickException("Database is not configured; no evaluation records were inserted.")
        if not confirm:
            raise click.ClickException(
                "This inserts synthetic/manual records into the configured database. "
                "Review the target and rerun with --confirm."
            )
        from services.search_evaluation import seed_evaluation_records

        try:
            result = seed_evaluation_records()
        except SQLAlchemyError as exc:
            db.session.rollback()
            app.logger.error(
                "Could not seed search evaluation records (%s).",
                type(exc).__name__,
            )
            raise click.ClickException("Evaluation fixtures could not be inserted.") from exc
        click.echo(
            f"Inserted {result['added']} synthetic/manual records; "
            f"skipped {result['skipped']} existing fixtures."
        )

    @app.cli.command("evaluate-search")
    def evaluate_search_command():
        if not app.config.get("DATABASE_ENABLED"):
            raise click.ClickException("Database is not configured; search evaluation is unavailable.")
        from services.search_evaluation import evaluate_search_cases

        try:
            evaluations = evaluate_search_cases()
        except SQLAlchemyError as exc:
            db.session.rollback()
            app.logger.error("Search evaluation failed (%s).", type(exc).__name__)
            raise click.ClickException("Search evaluation is temporarily unavailable.") from exc
        for evaluation in evaluations:
            case = evaluation["case"]
            precision = evaluation["precision"]
            recall = evaluation["recall"]
            click.echo(
                f"{case.label}: query={case.query!r}, expected={list(case.expected_names)!r}, "
                f"actual={evaluation['actual_names']!r}, "
                f"precision={'N/A' if precision is None else f'{precision:.3f}'}, "
                f"recall={'N/A' if recall is None else f'{recall:.3f}'}"
            )
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=app.config.get("DEBUG", False))
