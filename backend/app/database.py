"""
Database configuration: one SQLAlchemy engine (connection pool) for the app,
and a get_db() dependency that gives each request its own session.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",          # PyMySQL: pure-Python MySQL driver
    username=settings.db_user,
    password=settings.db_password,
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
    query={"charset": "utf8mb4"},
)

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=5, pool_pre_ping=True)


@event.listens_for(engine, "connect")
def identify_application(dbapi_connection, _record):
    """Every connection says who it is, so audit_logs.changed_by shows 'api'."""
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET @app_user = 'api'")


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: open a session for one request and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
