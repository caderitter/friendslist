import sqlite3
import pytest


@pytest.fixture(scope="function")
def db_connection():
    # Create a new in-memory database for each test
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()
