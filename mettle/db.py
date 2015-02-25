import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def parse_pgurl(db_url):
    """
    Given a SQLAlchemy-compatible Postgres url, return a dict with
    keys for user, password, host, port, and database.
    """

    parsed = urlparse.urlsplit(db_url)
    return {
        'user': parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/'),
        'host': parsed.hostname,
        'port': parsed.port,
    }

def make_session_cls(db_url, echo=False):
    return sessionmaker(bind=create_engine(db_url, echo=echo))
