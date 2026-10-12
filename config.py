import os
from sqlalchemy.engine import URL

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _build_mysql_database_url():
    host = os.environ.get("MYSQL_HOST", "").strip()
    user = os.environ.get("MYSQL_USER", "").strip()
    password = os.environ.get("MYSQL_PASSWORD", "")
    database = os.environ.get("MYSQL_DATABASE", "").strip()
    port = os.environ.get("MYSQL_PORT", "3306").strip()

    if not host or not user or not database:
        return None

    query = {}
    ssl_ca = os.environ.get("MYSQL_SSL_CA", "").strip()
    if ssl_ca:
        query["ssl-ca"] = ssl_ca

    return str(
        URL.create(
            drivername="mysql+pymysql",
            username=user,
            password=password,
            host=host,
            port=int(port or 3306),
            database=database,
            query=query,
        )
    )


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "courtvision-local-dev-secret")
    DATA_DIR = os.path.join(BASE_DIR, "data")
    API_KEY = os.environ.get("BALDONTLIE_API_KEY")
    AI_SERVICE_API_KEY = os.environ.get("AI_SERVICE_API_KEY")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEFAULT_SQLITE_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'courtvision.db')}"
    SQLALCHEMY_DATABASE_URI = (
        _build_mysql_database_url()
        or os.environ.get("DATABASE_URL")
        or DEFAULT_SQLITE_DATABASE_URI
    )
    DATABASE_ENABLED = bool(
        _build_mysql_database_url() or os.environ.get("DATABASE_URL") or DEFAULT_SQLITE_DATABASE_URI
    )
    DATABASE_STATUS_MESSAGE = "Using the local SQLite database. Set MYSQL_* environment variables to switch to MySQL persistence."


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    DATABASE_ENABLED = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
