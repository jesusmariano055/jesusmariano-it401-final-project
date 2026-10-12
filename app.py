import os

import click
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

from config import config
from extensions import db
from routes.main import register_routes


load_dotenv()


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    with app.app_context():
        db.create_all()

    csrf = CSRFProtect()
    csrf.init_app(app)

    @app.cli.command("init-db")
    def init_db_command():
        if not app.config.get("DATABASE_ENABLED"):
            raise click.ClickException(
                "Database is not configured. Set MYSQL_HOST, MYSQL_DATABASE, MYSQL_USER, and MYSQL_PASSWORD before running init-db."
            )
        db.create_all()
        click.echo("Initialized CourtVision application tables.")

    register_routes(app)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=app.config.get("DEBUG", False))
