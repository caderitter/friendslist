import pytest
from unittest.mock import patch, mock_open
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))

parent_dir = os.path.dirname(current_dir)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from db import get_db_connection, init_db


@pytest.fixture(scope="function")
def db_connection():
    # Create a new in-memory database for each test
    conn = get_db_connection(":memory:")

    fake_csv_data = "name,email\nAlice,alice@gmail.com\nBob,bob@gmail.com\n"

    # mock the csv read to return fake data before initializing db
    with patch("builtins.open", mock_open(read_data=fake_csv_data)):
        init_db(conn, "fake_path.csv")
        yield conn
        conn.close()
