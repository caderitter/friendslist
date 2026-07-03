from datetime import timedelta
import csv
import logging

from config import config


logger = logging.getLogger(__name__)
FRIENDS_CSV_PATH = config["server"]["friends_csv_path"]


def init_db(conn):
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
    with open(FRIENDS_CSV_PATH, "r", encoding="utf-8") as file:
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
            file_path TEXT NOT NULL,
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            friend_id INTEGER REFERENCES friends(id),
            date DATE NOT NULL,
            description TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS start_date (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL
        )
    """)
    conn.commit()


def insert_message(conn, email, subject, body_plain, body_html, attachment_paths):
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
    cur.execute(
        "INSERT INTO messages (friend_id, subject, body_plain, body_html) VALUES (?, ?, ?, ?)",
        (friend_id, subject, body_plain, body_html),
    )

    message_id = cur.lastrowid
    for path in attachment_paths:
        cur.execute(
            "INSERT INTO attachments (message_id, file_path) VALUES (?, ?)",
            (message_id, path),
        )
    conn.commit()


def get_all_messages_for_delta(conn, datetime, delta_days):
    """
    Retrieve all messages received between the given date and given date minus delta_days.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT f.name, f.email, a.file_path, e.date, e.description, m.subject, m.body_plain, m.body_html, m.received_at
        FROM messages m
        JOIN friends f ON m.friend_id = f.id
        JOIN attachments a ON m.id = a.message_id
        JOIN events e ON f.id = e.friend_id
        WHERE m.received_at BETWEEN ? AND ?
        ORDER BY m.received_at DESC
    """,
        (datetime - timedelta(days=delta_days), datetime),
    )

    messages = cur.fetchall()
    return messages


def get_start_date(conn):
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


def update_start_date(conn, new_date):
    """
    Update the start date in the database.
    """
    cur = conn.cursor()
    cur.execute("DELETE FROM start_date")  # Clear existing start date
    cur.execute("INSERT INTO start_date (date) VALUES (?)", (new_date,))
    conn.commit()
