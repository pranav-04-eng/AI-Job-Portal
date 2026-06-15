"""Tiny SQLAlchemy helper so each service can stand up its own SQLite DB.

Usage in a service:

    from common.db import Base, make_session, init_db
    from .models import User            # models subclass Base
    SessionLocal = make_session(db_path("auth"))
    init_db(db_path("auth"))            # create_all at startup

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def _engine(url: str):
    # check_same_thread=False: uvicorn serves requests across threads.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


def make_session(url: str):
    return sessionmaker(bind=_engine(url), autoflush=False, autocommit=False, future=True)


def init_db(url: str):
    """Create all tables registered on Base for this service's DB."""
    Base.metadata.create_all(_engine(url))
