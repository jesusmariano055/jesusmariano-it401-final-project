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


def _configured_mysql_url():
    url = os.environ.get("DATABASE_URL", "").strip()
    if url.startswith("mysql://"):
        return url.replace("mysql://", "mysql+pymysql://", 1)
    if url.startswith("mysql+pymysql://"):
        return url
    return None


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "courtvision-local-dev-secret")
    DATA_DIR = os.path.join(BASE_DIR, "data")
    API_KEY = os.environ.get("BALDONTLIE_API_KEY")
    AI_SERVICE_API_KEY = os.environ.get("AI_SERVICE_API_KEY")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
    MYSQL_DATABASE_URL = _build_mysql_database_url()
    CONFIGURED_MYSQL_URL = _configured_mysql_url()
    DISABLED_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_DATABASE_URI = (
        MYSQL_DATABASE_URL
        or CONFIGURED_MYSQL_URL
        or DISABLED_DATABASE_URI
    )
    DATABASE_ENABLED = bool(MYSQL_DATABASE_URL or CONFIGURED_MYSQL_URL)
    DATABASE_STATUS_MESSAGE = (
        "Saved-player features require a configured database. Set MYSQL_* variables "
        "to enable persistence; Explore and Team Intelligence remain available."
    )


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
