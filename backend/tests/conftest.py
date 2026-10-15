"""
Shared test fixtures. These tests run against the real MySQL database from .env
(load it first with ./etl/scripts/load_demo_data.sh).

Most database tests run inside a transaction that is ROLLED BACK at the end,
so they leave no trace. The payment tests must COMMIT (the stored procedure
commits itself); they use their own reference numbers and clean up afterwards.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import engine
from app.main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture
def conn():
    """A connection inside a transaction that is always rolled back."""
    with engine.connect() as connection:
        transaction = connection.begin()
        connection.execute(text("SET @app_user = 'pytest'"))
        yield connection
        transaction.rollback()


def scalar(connection, sql, **params):
    return connection.execute(text(sql), params).scalar()
