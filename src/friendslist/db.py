from datetime import datetime, timedelta, date, timezone
import csv
import json
import logging
import sqlite3


logger = logging.getLogger(__name__)


def to_utc(dt: datetime) -> datetime:
    """Convert aware or local-naive datetimes to naive UTC for SQLite storage/queries."""
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def get_db_connection(db_name):
    conn = sqlite3.connect(
        db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection, friends_csv_path: str):
    """
    Create the database and tables if they don't exist, and populate
    the friends table from a CSV file.
    """
    logger.debug("Initializing the database...")

    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
    """)
    logger.debug("Populating the friends table from friends csv...")
    with open(friends_csv_path, "r", encoding="utf-8") as file:
        csv_reader = csv.reader(file)
        next(csv_reader)  # Skip the header row

        cur.executemany(
            "INSERT OR IGNORE INTO friends (name, email) VALUES (?, ?);",
            csv_reader,
        )

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            friend_id INTEGER REFERENCES friends(id),
            subject TEXT NOT NULL,
            body_plain TEXT,
            body_html TEXT,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER REFERENCES messages(id),
            file_path TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS start_date (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL
        )
    """)
    conn.commit()


def insert_message(
    conn: sqlite3.Connection,
    received_at: datetime,
    email: str,
    subject: str,
    body_plain: str,
    body_html: str,
    attachment_paths: list[str],
):
    """
    Insert a new message into the database.
    """
    logger.debug("Inserting a new message into the database.")
    cur = conn.cursor()
    cur.execute("SELECT id FROM friends WHERE email = ?", (email,))
    friend_row = cur.fetchone()
    if not friend_row:
        raise ValueError(f"No friend found with email: {email}")

    friend_id = friend_row[0]
    # Naive UTC — SQLite's datetime() returns NULL for values with %z offsets.
    timestamp = to_utc(received_at).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO messages (friend_id, received_at, subject, body_plain, body_html) VALUES (?, ?, ?, ?, ?)",
        (friend_id, timestamp, subject, body_plain, body_html),
    )

    message_id = cur.lastrowid
    for path in attachment_paths:
        cur.execute(
            "INSERT INTO attachments (message_id, file_path) VALUES (?, ?)",
            (message_id, path),
        )
    conn.commit()


def get_all_messages_for_delta(
    conn: sqlite3.Connection, current_date: datetime, delta_days: int
):
    """
    Retrieve all messages received between the given date and given date minus delta_days.
    """
    end = to_utc(current_date)
    start = end - timedelta(days=delta_days)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 
            f.name, 
            f.email, 
            json_group_array(
                json_object('file_path', a.file_path, 'id', a.id)
            ) AS attachments, 
            m.subject, 
            m.body_plain, 
            m.body_html, 
            datetime(m.received_at, 'localtime') as 'received_at [timestamp]'
        FROM messages m
        JOIN friends f ON m.friend_id = f.id
        LEFT JOIN attachments a ON m.id = a.message_id
        WHERE datetime(received_at) BETWEEN datetime(?) AND datetime(?)
        GROUP BY m.id
        ORDER BY m.received_at DESC
    """,
        (start, end),
    )

    messages = [dict(row) for row in cur.fetchall()]
    # convert the json_group_array string into an array of { file_path: 'path', id: 'id' }
    for message in messages:
        attachments = message["attachments"]
        message["attachments"] = [
            a for a in json.loads(attachments) if a["id"] is not None
        ]
    return messages


def get_start_date(conn: sqlite3.Connection):
    """
    Retrieve the start date from the database.
    """
    cur = conn.cursor()
    cur.execute("SELECT date FROM start_date ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if row:
        return row[0]
    else:
        return None


def update_start_date(conn: sqlite3.Connection, new_date: date):
    """
    Update the start date in the database.
    """
    cur = conn.cursor()
    cur.execute("DELETE FROM start_date")  # Clear existing start date
    cur.execute("INSERT INTO start_date (date) VALUES (?)", (new_date,))
    conn.commit()


def get_addresses_dict(conn: sqlite3.Connection) -> dict[str, str]:
    cur = conn.cursor()
    cur.execute("SELECT email, name FROM friends")
    rows = cur.fetchall()
    return {email: name for email, name in rows}
